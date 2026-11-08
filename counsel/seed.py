"""Create the fictional firm from seed/ and the prepared generator."""
import json
import os
import re
from pathlib import Path

from . import db, masking, prepared

ROOT = Path(__file__).parent.parent
DATA = Path(os.environ.get("SH_DATA", ROOT / "data"))


def load():
    return json.loads((ROOT / "seed" / "users.json").read_text())


def firm(data_dir=None):
    """Seed users, matters, documents and masking defaults into an empty database."""
    db.init()
    if db.one("SELECT id FROM users LIMIT 1"):
        return
    seed = load()
    for u in seed["users"]:
        db.run("INSERT INTO users VALUES (?,?,?,?,?)", u["id"], u["name"], u["role"], u["title"], u["pin"])
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
