"""Masking for public text going to Claude. Privileged text is never masked and sent. It is not sent.

The key (tag to value) stays on the box. Detection failure blocks the cloud call.
"""
import csv
import io
import json
import re

from . import db, llm

ALWAYS = [
    ("api_key", "API keys"), ("token", "Access tokens"), ("password", "Passwords"),
    ("gov_id", "Government IDs"), ("card", "Card numbers"), ("bank", "Bank account numbers"),
]
DEFAULTS = [("client", "Client and party names"), ("email", "Emails"), ("phone", "Phone numbers"), ("case", "Case numbers")]
TAG_NAME = {
    "client": "CLIENT", "email": "EMAIL", "phone": "PHONE", "case": "CASE", "api_key": "KEY", "token": "TOKEN",
    "password": "PASSWORD", "gov_id": "ID", "card": "CARD", "bank": "ACCOUNT", "people_full": "PERSON",
    "first_names": "PERSON", "last_names": "PERSON", "companies": "COMPANY", "addresses": "ADDRESS", "dates": "DATE",
    "money": "AMOUNT", "numbers": "NUMBER", "term": "TERM",
}
NOTE = (
    "Some values are replaced by placeholders like [CLIENT_1] or [PERSON_1]. Treat each one as the real value: "
    "copy it exactly, brackets included, wherever that value belongs in your answer."
)
RULE_CHOICES = {
    "people_full": "people's full names", "first_names": "first names", "last_names": "last names",
    "companies": "companies", "addresses": "addresses", "dates": "dates", "money": "money amounts",
    "numbers": "all numbers", "other": "something else",
}


class MaskError(Exception):
    pass


def seed_defaults():
    for key, label in ALWAYS:
        db.run("INSERT INTO mask_items (grp, key, label, enabled, ts) VALUES ('always',?,?,1,?)", key, label, db.now())
    for key, label in DEFAULTS:
        db.run("INSERT INTO mask_items (grp, key, label, enabled, ts) VALUES ('default',?,?,1,?)", key, label, db.now())


def party_names():
    """Full party names and their distinctive first or last word, longest first."""
    names = set()
    for row in db.all("SELECT parties FROM matters"):
        for party in json.loads(row["parties"]):
            names.add(party)
            words = party.split()
            if len(words) >= 2:
                short = words[-1] if party in ("Helen Rourke",) else words[0]
                if len(short) >= 5:
                    names.add(short)
    return sorted(names, key=len, reverse=True)


def luhn(digits):
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


PATTERNS = {
    "api_key": re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,})"),
    "gov_id": re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"(?<![\d-])(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"),
    "case": re.compile(r"\bCGC-\d{2}-\d{6}\b"),
    "addresses": re.compile(r"\b\d{1,5}\s+(?:[A-Z][a-z]+\s+){1,3}(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Lane|Ln|Dr|Drive|Way)\b\.?"),
    "dates": re.compile(
        r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:\s+\d{4})?\b"
        r"|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,?\s+\d{4})?\b"
    ),
    "money": re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?k?\b|\b\d[\d,]*(?:\.\d+)?\s?dollars\b", re.I),
    "numbers": re.compile(r"(?<![\w.,-])\d[\d,.]*(?!\w)"),
    "companies": re.compile(r"\b(?:[A-Z][a-z]+\s+){1,3}(?:Inc|LLC|Corp|Ltd|Co)\b\.?"),
}
GROUP_PATTERNS = {
    "token": re.compile(r"\b(?:access[_ -]?token|auth[_ -]?token|bearer)\b\s*[:=]?\s*([A-Za-z0-9._-]{16,})", re.I),
    "password": re.compile(r"\b(?:password|passcode|pwd)\b\s*(?:is|:|=)\s*(\S+)", re.I),
    "bank": re.compile(r"\b(?:account|acct|iban|routing)\b[^\d\n]{0,15}(\d{6,17})\b", re.I),
}
CARD = re.compile(r"(?<![\d-])\d(?:[ -]?\d){12,18}(?!\d)")


MAX_TERM = 200
MAX_TERMS = 20000
MAX_FILE_CHARS = 2_000_000
HEADER_WORDS = {"name", "names", "full name", "first name", "last name", "email", "e-mail", "phone", "address", "ssn", "client", "party", "id", "notes"}
PERSON = re.compile(r"^[^\W\d_][\w.'’-]*(?: [^\W\d_][\w.'’-]*){0,3}$")
_firm_cache = (None, None)


def _normal(term):
    return " ".join(str(term).split())


def _kind(term):
    if PATTERNS["email"].fullmatch(term):
        return "email"
    if PATTERNS["phone"].fullmatch(term):
        return "phone"
    if PERSON.match(term) and term[0].isupper():
        return "people_full"
    return "term"


def _usable(term):
    """A one-letter or short numeric entry would mask ordinary words and numbers everywhere."""
    return 2 <= len(term) <= MAX_TERM and not (term.isdigit() and len(term) < 5)


def _firm_matcher():
    """One compiled pattern for the firm's list, rebuilt only when the list changes."""
    global _firm_cache
    stamp = db.one("SELECT COUNT(*) n, MAX(id) top FROM mask_terms")
    stamp = (db.path(), stamp["n"], stamp["top"])
    if _firm_cache[0] == stamp:
        return _firm_cache[1]
    rows = db.all("SELECT term, kind FROM mask_terms")
    matcher = None
    if rows:
        kinds = {r["term"].lower(): r["kind"] for r in rows}
        alternatives = "|".join(re.escape(t).replace(r"\ ", r"\s+") for t in sorted(kinds, key=len, reverse=True))
        matcher = (re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)", re.I), kinds)
    _firm_cache = (stamp, matcher)
    return matcher


def parse_terms(filename, text):
    """Entries from an uploaded .txt (one per line) or .csv (every cell, header row skipped)."""
    name = filename.lower()
    if not name.endswith((".txt", ".csv")):
        raise ValueError("Upload a .txt or .csv file.")
    if len(text) > MAX_FILE_CHARS:
        raise ValueError("That file is too large.")
    if name.endswith(".txt"):
        return [_normal(line) for line in text.splitlines() if line.strip()]
    rows = [[_normal(cell) for cell in row if cell.strip()] for row in csv.reader(io.StringIO(text))]
    rows = [row for row in rows if row]
    if rows and any(cell.lower() in HEADER_WORDS for cell in rows[0]) and not any("@" in c or any(ch.isdigit() for ch in c) for c in rows[0]):
        rows = rows[1:]
    return [cell for row in rows for cell in row]


def add_terms(user_id, values, source):
    """Add entries to the firm's list. Returns how many were added, already there, and skipped."""
    cleaned = [_normal(v) for v in values]
    usable = list({v.lower(): v for v in cleaned if _usable(v)}.values())
    have = db.one("SELECT COUNT(*) n FROM mask_terms")["n"]
    if have + len(usable) > MAX_TERMS:
        raise ValueError(f"The firm's list holds up to {MAX_TERMS:,} entries.")
    connection = db.conn()
    connection.execute("BEGIN IMMEDIATE")
    try:
        added = 0
        for term in usable:
            added += connection.execute(
                "INSERT OR IGNORE INTO mask_terms (term, kind, source, added_by, ts) VALUES (?,?,?,?,?)",
                (term, _kind(term), source, user_id, db.now()),
            ).rowcount
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    return {"added": added, "existing": len(usable) - added, "skipped": len(cleaned) - len(usable)}


def _spans(text, items, find_people):
    spans = []

    def add(start, end, kind):
        spans.append((start, end, kind))

    for key in ("api_key", "gov_id"):
        for m in PATTERNS[key].finditer(text):
            add(m.start(), m.end(), key)
    for key, pattern in GROUP_PATTERNS.items():
        for m in pattern.finditer(text):
            add(m.start(1), m.end(1), key)
    for m in CARD.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and luhn(digits):
            add(m.start(), m.end(), "card")

    enabled = {i["key"] for i in items if i["enabled"]}
    for key in ("email", "phone", "case"):
        if key in enabled:
            for m in PATTERNS[key].finditer(text):
                add(m.start(), m.end(), key)
    if "client" in enabled:
        for name in party_names():
            for m in re.finditer(rf"(?<![\w]){re.escape(name)}(?![\w])", text):
                add(m.start(), m.end(), "client")

    matcher = _firm_matcher()
    if matcher:
        pattern, kinds = matcher
        for m in pattern.finditer(text):
            add(m.start(), m.end(), kinds.get(_normal(m.group()).lower(), "term"))

    for item in items:
        if item["grp"] != "added" or not item["enabled"]:
            continue
        key = item["key"]
        if key in ("addresses", "dates", "money", "companies", "numbers"):
            for m in PATTERNS[key].finditer(text):
                add(m.start(), m.end(), key)
        elif key == "term":
            for term in json.loads(item["terms"] or "[]"):
                for m in re.finditer(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.I):
                    add(m.start(), m.end(), "term")
        elif key in ("people_full", "first_names", "last_names"):
            if find_people is None:
                raise MaskError("name finder unavailable")
            for full in find_people(text):
                if not full or full not in text:
                    continue
                words = full.split()
                targets = {"people_full": [full], "first_names": words[:1], "last_names": words[-1:]}[key]
                for target in targets:
                    for m in re.finditer(rf"(?<!\w){re.escape(target)}(?!\w)", text):
                        add(m.start(), m.end(), key)
    return spans


def mask(text, find_people=None):
    """Return (masked_text, keymap, tags). Raises MaskError so the caller can block the call."""
    try:
        items = db.all("SELECT * FROM mask_items")
        spans = _spans(text, items, find_people)
        spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
        kept, last_end = [], 0
        for start, end, kind in spans:
            if start >= last_end:
                kept.append((start, end, kind))
                last_end = end
        counters, by_value, out, cursor = {}, {}, [], 0
        for start, end, kind in kept:
            value = text[start:end]
            if value not in by_value:
                name = TAG_NAME[kind]
                counters[name] = counters.get(name, 0) + 1
                by_value[value] = f"[{name}_{counters[name]}]"
            out.append(text[cursor:start])
            out.append(by_value[value])
            cursor = end
        out.append(text[cursor:])
        key = {tag: value for value, tag in by_value.items()}
        return "".join(out), key, list(key)
    except MaskError:
        raise
    except Exception as e:
        raise MaskError(str(e)) from e


TAG_RE = re.compile(r"\[[A-Z]+_\d+\]")


def restore(text, keymap):
    """Swap tags back. Returns (restored, notes) with a note for any changed or missing tag."""
    notes = []
    restored = text
    for tag, value in keymap.items():
        if tag not in text:
            notes.append(f"{tag} missing from reply")
        restored = restored.replace(tag, value)
    for tag in set(TAG_RE.findall(text)):
        if tag not in keymap:
            notes.append(f"{tag} changed in reply")
    return restored, notes


RULE_START = re.compile(r"^\s*(?:please\s+)?(mask|hide|redact|anonymi[sz]e|stop masking|don'?t send|do not send|never send)\b", re.I)
RULE_ANY = re.compile(r"\b(don'?t|do not|never)\b.{0,60}?\b(send|share)\b.{0,60}?\b(cloud|claude|outside)\b", re.I | re.S)
RULE_ADD = re.compile(r"\b(?:add|create|new)\b.{0,40}\bmask(?:ing)?\b|\b(?:from now on|always)\b.{0,40}\b(?:mask|hide|redact)\b|\bmask(?:ing)? (?:rule|all|every)\b", re.I | re.S)
OFF_WORDS = re.compile(r"\b(stop|unmask|turn off)\b", re.I)


def is_privacy_rule(text):
    return len(text) < 300 and bool(RULE_START.search(text) or RULE_ANY.search(text) or RULE_ADD.search(text))


DEFAULT_WORDS = {"client": r"\bclients?\b|\bpart(?:y|ies)\b", "email": r"\be-?mails?\b", "phone": r"\bphones?\b", "case": r"\bcase numbers?\b"}


def apply_rule(user_id, text):
    """Turn plain words into a masking list item. Returns the one-line reply."""
    try:
        answers, _ = llm.d1_decide(text, {
            "item": {"type": "choice", "instructions": "What does this person want masked before text goes to the cloud?", "criteria": RULE_CHOICES},
            "off": {"type": "noul", "instructions": "Does this message turn masking off for something, rather than adding masking?"},
        })
    except llm.LocalError:
        return "Couldn't read that rule. Nothing changed."

    choice, confidence = answers["item"]["choice"], answers["item"]["confidence"]
    if OFF_WORDS.search(text) and answers["off"]["noul"] >= 0.5:
        for key, words in DEFAULT_WORDS.items():
            if re.search(words, text, re.I):
                db.run("UPDATE mask_items SET enabled=0 WHERE grp='default' AND key=?", key)
                label = next(l for k, l in DEFAULTS if k == key)
                return f"Masking turned off: {label.lower()}."
        return "Only default items can be turned off."

    for key, words in DEFAULT_WORDS.items():
        if re.search(words, text, re.I) and not OFF_WORDS.search(text):
            label = next(l for k, l in DEFAULTS if k == key)
            db.run("UPDATE mask_items SET enabled=1 WHERE grp='default' AND key=?", key)
            return f"Already masked: {label.lower()}."

    terms = re.findall(r"[\"“']([^\"”']{2,})[\"”']", text)
    if not terms:
        terms = [t for t in re.findall(r"(?<=[a-z,] )[A-Z][\w-]+(?: [A-Z][\w-]+)*", text)]
    if terms and (choice == "other" or confidence < 0.5):
        label = ", ".join(terms)
        db.run("INSERT INTO mask_items (grp, key, label, enabled, added_by, words, terms, ts) VALUES ('added','term',?,1,?,?,?,?)",
               label, user_id, text, json.dumps(terms), db.now())
        return f"Added to masking: {label}."
    if confidence < 0.5 or choice == "other":
        return "Which should I mask: people's names, companies, addresses, dates, money amounts or all numbers?"

    label = RULE_CHOICES[choice]
    existing = db.one("SELECT id FROM mask_items WHERE grp='added' AND key=?", choice)
    if not existing:
        db.run("INSERT INTO mask_items (grp, key, label, enabled, added_by, words, ts) VALUES ('added',?,?,1,?,?,?)",
               choice, label, user_id, text, db.now())
    return f"Added to masking: {label}."
