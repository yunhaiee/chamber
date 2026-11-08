"""The managing partner's log. One table, written once, never updated, hash-chained."""
import csv
import hashlib
import io
import json
import threading

from . import db

_lock = threading.Lock()
GENESIS = "0" * 64


def _digest(prev_hash, ts, actor, event, dest, sentence, payload_id):
    content = json.dumps([ts, actor, event, dest, sentence, payload_id], separators=(",", ":"))
    return hashlib.sha256((prev_hash + content).encode()).hexdigest()


def append(actor, event, dest, sentence, payload_id=None):
    with _lock:
        last = db.one("SELECT hash FROM audit ORDER BY id DESC LIMIT 1")
        prev_hash = last["hash"] if last else GENESIS
        ts = round(db.now(), 3)
        digest = _digest(prev_hash, ts, actor, event, dest, sentence, payload_id)
        return db.run(
            "INSERT INTO audit (ts, actor, event, dest, sentence, payload_id, prev_hash, hash) VALUES (?,?,?,?,?,?,?,?)",
            ts, actor, event, dest, sentence, payload_id, prev_hash, digest,
        )


def verify():
    """Return {"intact": True} or {"intact": False, "first_bad": id}."""
    prev_hash = GENESIS
    for row in db.all("SELECT * FROM audit ORDER BY id"):
        expected = _digest(prev_hash, row["ts"], row["actor"], row["event"], row["dest"], row["sentence"], row["payload_id"])
        if row["prev_hash"] != prev_hash or row["hash"] != expected:
            return {"intact": False, "first_bad": row["id"]}
        prev_hash = row["hash"]
    return {"intact": True, "first_bad": None}


DESTS = ("box", "claude", "lawyer", "blocked")


def entries(user=None, dest=None):
    sql, args = "SELECT * FROM audit WHERE 1=1", []
    if user:
        sql += " AND actor=?"
        args.append(user)
    if dest:
        sql += " AND dest=?"
        args.append(dest)
    return db.all(sql + " ORDER BY id DESC", *args)


def totals():
    counts = {d: 0 for d in DESTS}
    for row in db.all("SELECT dest, COUNT(*) n FROM audit WHERE dest IS NOT NULL GROUP BY dest"):
        if row["dest"] in counts:
            counts[row["dest"]] = row["n"]
    counts["requests"] = sum(counts[d] for d in DESTS)
    return counts


def csv_text():
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["id", "time", "actor", "event", "destination", "sentence", "hash"])
    for row in db.all("SELECT * FROM audit ORDER BY id"):
        writer.writerow([row["id"], row["ts"], row["actor"], row["event"], row["dest"], row["sentence"], row["hash"]])
    return out.getvalue()
