"""Create the fictional firm from seed/ and the prepared generator."""
import json
import os
import re
from pathlib import Path

from . import db, masking, prepared

ROOT = Path(__file__).parent.parent
DATA = Path(os.environ.get("SH_DATA", ROOT / "data"))


HISTORY = ("requests", "evidence", "cloud_evidence", "row_events", "queue", "audit", "cloud_payloads",
           "actions", "try_pointer", "user_models", "mask_items", "mask_terms")


def load():
    return json.loads((ROOT / "seed" / "users.json").read_text())


def clear_history():
    """Everything people did goes, in one transaction. The firm and signed-in sessions stay."""
    connection = db.conn()
    connection.execute("BEGIN IMMEDIATE")
    try:
        for table in HISTORY:
            connection.execute(f"DELETE FROM {table}")
        masking.seed_defaults()
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def empty():
    """A real firm's database: tables and masking defaults, no fictional people."""
    db.init()
    if not db.one("SELECT id FROM mask_items LIMIT 1"):
        masking.seed_defaults()


def firm(data_dir=None):
    """Seed users, matters, documents and masking defaults into an empty database."""
    db.init()
    if db.one("SELECT id FROM users LIMIT 1"):
        return
    seed = load()
    for u in seed["users"]:
        db.run("INSERT INTO users (id, name, role, title, pin, reports_to) VALUES (?,?,?,?,?,?)",
               u["id"], u["name"], u["role"], u["title"], u["pin"], u["reports_to"])
        for matter in u["matters"]:
            db.run("INSERT INTO memberships VALUES (?,?)", u["id"], matter)
    for m in seed["matters"]:
        db.run("INSERT INTO matters VALUES (?,?,?)", m["id"], m["name"], json.dumps(m["parties"]))
    root = Path(data_dir or os.environ.get("SH_DATA", DATA)) / "docs"
    for doc in prepared.catalog()["docs"]:
        folder = root / doc["matter"]
        folder.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", doc["title"].lower()).strip("-")
        path = folder / f"{slug}.txt"
        path.write_text(doc["body"])
        db.run(
            "INSERT INTO documents (matter_id, title, path, privileged, listed) VALUES (?,?,?,?,?)",
            doc["matter"], doc["title"], str(path), int(doc["privileged"]), int(doc["listed"]),
        )
    masking.seed_defaults()
