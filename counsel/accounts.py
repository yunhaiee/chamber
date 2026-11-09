"""People at the firm and who answers to whom: the head of firm, managers, employees."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3

from . import db

HEAD, MANAGER, EMPLOYEE = "head", "manager", "employee"
MANAGING = (HEAD, MANAGER)
MIN_PASSWORD = 8
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Invalid(Exception):
    """Something the person can fix. The message is shown to them."""


class NotAllowed(Exception):
    """Reported as not found, so nobody learns what is outside their reach."""


def demo_mode():
    return os.environ.get("SH_DEMO") == "1"


def hash_password(password):
    salt = os.urandom(16)
    return f"{salt.hex()}${_derive(password, salt).hex()}"


def _derive(password, salt):
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)


def check_password(password, stored):
    salt, digest = stored.split("$")
    return hmac.compare_digest(_derive(password, bytes.fromhex(salt)).hex(), digest)


_NOBODY = hash_password(secrets.token_hex(16))  # checked when the email is unknown, so timing doesn't reveal who has an account


def authenticate(email, password):
    user = db.one("SELECT * FROM users WHERE email=? COLLATE NOCASE AND active=1", email.strip())
    if check_password(password, user["pw_hash"] if user and user["pw_hash"] else _NOBODY) and user:
        return user
    return None


def needs_setup():
    return db.one("SELECT id FROM users LIMIT 1") is None


def firm_name():
    row = db.one("SELECT name FROM firm WHERE id=1")
    return row["name"] if row else ""


def _fields(body):
    name = str(body.get("name") or "").strip()
    email = str(body.get("email") or "").strip()
    password = str(body.get("password") or "")
    if not name or len(name) > 120:
        raise Invalid("Enter a name.")
    if not EMAIL.match(email):
        raise Invalid("Enter a valid email.")
    if len(password) < MIN_PASSWORD:
        raise Invalid(f"Use a password of at least {MIN_PASSWORD} characters.")
    return name, email, password, str(body.get("title") or "").strip()[:120]


def _insert(name, email, password, title, role, reports_to):
    user_id = secrets.token_hex(6)
    try:
        db.run("INSERT INTO users (id, name, role, title, email, pw_hash, reports_to, active) VALUES (?,?,?,?,?,?,?,1)",
               user_id, name, role, title, email, hash_password(password), reports_to)
    except sqlite3.IntegrityError as e:
        raise Invalid("Someone already uses that email.") from e
    return user_id


def setup(body):
    """Create the firm and its head. Works once, on an empty database."""
    firm = str(body.get("firm") or "").strip()
    if not firm or len(firm) > 160:
        raise Invalid("Enter the firm's name.")
    name, email, password, title = _fields(body)
    connection = db.conn()
    connection.execute("BEGIN IMMEDIATE")
    try:
        if not needs_setup():
            raise NotAllowed
        db.run("INSERT INTO firm (id, name, ts) VALUES (1,?,?)", firm, db.now())
        user_id = _insert(name, email, password, title or "Head of firm", HEAD, None)
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    return user_id


def reports(user_id):
    """Everyone below this person, at any depth."""
    return [r["id"] for r in db.all(
        """WITH RECURSIVE tree(id) AS (
             SELECT id FROM users WHERE reports_to=? AND active=1
             UNION SELECT u.id FROM users u JOIN tree t ON u.reports_to = t.id WHERE u.active=1)
           SELECT id FROM tree""", user_id)]


def visible_ids(user):
    """Whose work this person may oversee. The head sees everyone; a manager sees their own people."""
    if user["role"] == HEAD:
        return [r["id"] for r in db.all("SELECT id FROM users WHERE active=1 ORDER BY rowid")]
    if user["role"] == MANAGER:
        return [user["id"], *reports(user["id"])]
    return [user["id"]]


def supervisor(user_row):
    """Who a legal decision goes to. None only for the head, who has nobody above them."""
    boss_id = user_row.get("reports_to")
    boss = db.one("SELECT * FROM users WHERE id=? AND active=1", boss_id) if boss_id else None
    if boss or user_row.get("role") == HEAD:
        return boss
    return db.one("SELECT * FROM users WHERE role=? AND active=1 LIMIT 1", HEAD)


def team(actor):
    allowed = set(visible_ids(actor))
    rows = db.all("SELECT id, name, email, title, role, reports_to FROM users WHERE active=1 ORDER BY rowid")
    names = {r["id"]: r["name"] for r in rows}
    return {
        "people": [{**r, "reports_name": names.get(r["reports_to"], "")} for r in rows if r["id"] in allowed],
        "managers": [{"id": r["id"], "name": r["name"]} for r in rows if r["role"] in MANAGING and r["id"] in allowed],
        "is_head": actor["role"] == HEAD,
        "you": actor["id"],
    }


def _managing_person(user_id):
    row = db.one("SELECT id FROM users WHERE id=? AND active=1 AND role IN (?,?)", user_id, *MANAGING)
    if row is None:
        raise Invalid("Choose a manager or the head of firm to report to.")
    return row["id"]


def add(actor, body):
    name, email, password, title = _fields(body)
    role = str(body.get("role") or EMPLOYEE)
    if role not in (MANAGER, EMPLOYEE):
        raise Invalid("Choose manager or employee.")
    if actor["role"] == HEAD:
        reports_to = _managing_person(str(body.get("reports_to") or actor["id"]))
    elif role != EMPLOYEE:
        raise Invalid("Only the head of firm can add managers.")
    else:
        reports_to = actor["id"]
    return _insert(name, email, password, title, role, reports_to), name


def _target(user_id):
    row = db.one("SELECT * FROM users WHERE id=? AND active=1", user_id)
    if row is None or row["role"] == HEAD:
        raise NotAllowed
    return row


def update(user_id, body):
    """The head changes someone's role or who they report to."""
    target = _target(user_id)
    role = str(body.get("role") or target["role"])
    if role not in (MANAGER, EMPLOYEE):
        raise Invalid("Choose manager or employee.")
    reports_to = _managing_person(str(body.get("reports_to") or target["reports_to"]))
    if reports_to == user_id or reports_to in reports(user_id):
        raise Invalid("Someone can't report to a person who reports to them.")
    db.run("UPDATE users SET role=?, reports_to=? WHERE id=?", role, reports_to, user_id)
    if role == EMPLOYEE:
        db.run("UPDATE users SET reports_to=? WHERE reports_to=?", reports_to, user_id)
    return target["name"]


def remove(actor, user_id):
    """End someone's access. Their history stays; their people move up one level."""
    target = _target(user_id)
    if actor["role"] != HEAD and user_id not in reports(actor["id"]):
        raise NotAllowed
    db.run("UPDATE users SET reports_to=? WHERE reports_to=?", target["reports_to"], user_id)
    db.run("UPDATE users SET active=0, email=NULL, pw_hash=NULL WHERE id=?", user_id)
    db.run("DELETE FROM sessions WHERE user=?", user_id)
    return target["name"]
