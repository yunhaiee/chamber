"""The walls between lawyers. The server enforces these; the interface only reflects them."""
import re
from pathlib import Path

from . import db

NOT_FOUND = "No document called that in your matters."

_NOUNS = r"deposition|depo|will|trust|memo|letter|notes|transcript|instrument|email|worksheet|abstract"
_STOP = set("""
a an the this that these those my our his her their your me us of for to from by with in on at and or about
summarize summarise pull get show find open read review send draft tag list fetch give see attach use compute
please can could would should will do does did is are was were what who when how why which it its
new last first latest client clients family day
""".split())
_FETCH_VERB = re.compile(r"^\s*(please\s+)?(summari[sz]e|open|show|get|pull|read|find|fetch|review|tag|list)\b", re.I)


def matters_of(user):
    return [r["matter"] for r in db.all("SELECT matter FROM memberships WHERE user=?", user)]


def docs_for(user, listed_only=False):
    """Only this person's documents, by matter membership."""
    sql = (
        "SELECT d.* FROM documents d JOIN memberships m ON d.matter_id = m.matter WHERE m.user=?"
        + (" AND d.listed=1" if listed_only else "")
        + " ORDER BY d.id"
    )
    return db.all(sql, user)


def doc_if_visible(user, doc_id):
    return db.one(
        "SELECT d.* FROM documents d JOIN memberships m ON d.matter_id = m.matter WHERE m.user=? AND d.id=?",
        user, doc_id,
    )


def read(doc):
    return Path(doc["path"]).read_text()


def find_reference(user, text):
    """Decide whether typed text names a document.

    Returns ("attach", doc), ("denied", doc), ("missing", name) or None.
    "denied" and "missing" produce the same reply to the person.
    """
    for match in re.finditer(rf"\b({_NOUNS})\b", text, re.I):
        before = re.findall(r"[A-Za-z][\w'’-]*", text[: match.start()])[-3:]
        names = [re.sub(r"['’]s$", "", w) for w in before if w.lower() not in _STOP]
        if not names:
            continue
        wanted = [n.lower() for n in names]
        mine, others = [], []
        for doc in db.all("SELECT d.*, m.name AS matter_name, m.parties FROM documents d JOIN matters m ON d.matter_id = m.id ORDER BY d.id"):
            hay = f"{doc['title']} {doc['matter_name']} {doc['parties']}".lower()
            if all(w in hay for w in wanted):
                (mine if doc["matter_id"] in matters_of(user) else others).append(doc)
        if mine:
            return ("attach", mine[0])
        if others:
            return ("denied", others[0])
        if _FETCH_VERB.search(text) and any(n[0].isupper() for n in names):
            return ("missing", " ".join(names))
    return None
