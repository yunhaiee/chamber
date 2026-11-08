"""The leak test: scans every payload that went to the cloud for privileged material."""
import re
from pathlib import Path

from . import db, masking


def _words(text):
    return re.findall(r"[a-z0-9$§'-]+", text.lower())


_cache = {}


def _fixtures():
    if db.path() in _cache:
        return _cache[db.path()]
    secrets, emails, grams = set(), set(), set()
    for doc in db.all("SELECT path, privileged FROM documents"):
        path = Path(doc["path"])
        if not path.exists():
            continue
        body = path.read_text()
        secrets.update(re.findall(r"sk-test-[a-z0-9]{20}", body))
        emails.update(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", body))
        if doc["privileged"]:
            words = _words(body)
            grams.update(" ".join(words[i:i + 8]) for i in range(len(words) - 7))
    _cache[db.path()] = (secrets, emails, grams)
    return secrets, emails, grams


def scan():
    """Return {"payloads": n, "hits": [{"payload_id", "what"}]}. Must find zero hits."""
    secrets, emails, grams = _fixtures()
    parties = masking.party_names()
    hits = []
    rows = db.all("SELECT id, user_text FROM cloud_payloads ORDER BY id")
    for row in rows:
        text = row["user_text"] or ""
        for value in secrets | emails:
            if value in text:
                hits.append({"payload_id": row["id"], "what": "secret or email"})
        for party in parties:
            if re.search(rf"(?<!\w){re.escape(party)}(?!\w)", text):
                hits.append({"payload_id": row["id"], "what": f"party {party}"})
        words = _words(text)
        for i in range(len(words) - 7):
            if " ".join(words[i:i + 8]) in grams:
                hits.append({"payload_id": row["id"], "what": "privileged text run"})
                break
    return {"payloads": len(rows), "hits": hits}
