"""Deterministic checks. Every check compares a reply to known fixture values.

No model grades another model. Normalizers accept the ordinary ways of writing
the same number, date or citation: 42k / 42,000 / 42000, 14 August / Aug 14 /
2026-08-14, section 337 / § 337 / CCP 337.
"""
import re

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"


def text_of(answer):
    """Flatten a model's answer (string, list or object) to searchable text."""
    if answer is None:
        return ""
    if isinstance(answer, str):
        return answer
    if isinstance(answer, dict):
        return "\n".join(f"{k}: {text_of(v)}" for k, v in answer.items())
    if isinstance(answer, (list, tuple)):
        return "\n".join(text_of(v) for v in answer)
    return str(answer)


def numbers_in(text):
    """Every number in the text as a normalized string: 42k -> 42000, 1840.50 -> 1840.5."""
    found = set()
    for m in re.finditer(r"(?<![\w.])\$?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s?([kK]\b)?", text):
        value = float(m.group(1).replace(",", "") + (m.group(2) or ""))
        if m.group(3):
            value *= 1000
        found.add(norm_number(value))
    return found


def norm_number(value):
    value = float(str(value).replace(",", "").replace("$", ""))
    return str(int(value)) if value == int(value) else f"{value:.10f}".rstrip("0")


def has_number(text, value):
    return norm_number(value) in numbers_in(text)


def dates_in(text):
    """Every date in the text as (month, day), with the year when one is written."""
    found = set()
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        found.add((int(m.group(2)), int(m.group(3))))
        found.add((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in re.finditer(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?{_MONTH}\.?(?:,?\s+(\d{{4}}))?", text, re.I):
        _add_date(found, m.group(2), m.group(1), m.group(3))
    for m in re.finditer(rf"\b{_MONTH}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b", text, re.I):
        _add_date(found, m.group(1), m.group(2), m.group(3))
    return found


def _add_date(found, month, day, year):
    month_number = MONTHS[month[:3].lower()]
    found.add((month_number, int(day)))
    if year:
        found.add((int(year), month_number, int(day)))


def norm_date(value):
    """Parse a date in any accepted form to (year, month, day) or (month, day)."""
    found = dates_in(str(value))
    return next((d for d in found if len(d) == 3), next(iter(found), None))


def has_date(text, value):
    target = norm_date(value)
    return target is not None and target in dates_in(text)


def norm_section(value):
    """'§ 338(d)', 'section 338(d)', 'CCP 338(d)' -> '338(d)'. Rule forms keep their rule number."""
    text = str(value).lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"^(§+|sections?|sec\.?|ccp|codeciv\.?proc\.?|code ?of ?civil ?procedure|prob\.?code|probatecode)", "", text)
    text = re.sub(r"^§+", "", text)
    return text


def _section_pattern(section):
    body = re.escape(norm_section(section))
    return re.compile(rf"(?<![\d.]){body}(?![\d])", re.I)


def has_section(text, section):
    compact = re.sub(r"\s+", "", text)
    return _section_pattern(section).search(compact) is not None


def _minutes(hour, minute, meridiem):
    hour = int(hour) % 12 + (12 if meridiem and meridiem[0].lower() == "p" else 0) if meridiem else int(hour)
    return hour * 60 + int(minute)


def has_time(text, value):
    """06:30, 6:30 and 6:30 AM are the same time."""
    hour, minute = str(value).split(":")
    target = _minutes(hour, minute, None)
    for m in re.finditer(r"(?<![\d:])(\d{1,2})[:.](\d{2})(?![\d:])\s*([ap]\.?m\b)?", text, re.I):
        if _minutes(m.group(1), m.group(2), m.group(3)) == target:
            return True
    return False


def has_fact(text, fact):
    """A required fact: number, date, time or name."""
    kind, value = fact["type"], fact["value"]
    if kind == "number":
        return has_number(text, value)
    if kind == "date":
        return has_date(text, value)
    if kind == "time":
        return has_time(text, value)
    if kind == "text":
        return re.sub(r"\s+", " ", value).lower() in re.sub(r"\s+", " ", text).lower()
    raise ValueError(kind)


def run(check, parsed, original_len=None):
    """Grade a parsed model reply. Returns {"ok": bool, "items": [{name, ok}], "reason": str}."""
    if not isinstance(parsed, dict) or "answer" not in parsed:
        return {"ok": False, "items": [{"name": "valid JSON", "ok": False}], "reason": "no JSON"}
    answer = parsed["answer"]
    text = text_of(answer)
    if not text.strip():
        return {"ok": False, "items": [{"name": "answer", "ok": False}], "reason": "empty"}
    items = []
    kind = check["type"]

    if kind == "facts":
        for fact in check["facts"]:
            items.append({"name": fact["value"], "ok": has_fact(text, fact)})
        if check.get("max_ratio") and original_len:
            limit = int(original_len * check["max_ratio"])
            items.append({"name": f"length <= {limit}", "ok": len(text) <= limit})
        for banned in check.get("forbid", []):
            items.append({"name": f"omits {banned}", "ok": banned.lower() not in text.lower()})
        for banned in check.get("forbid_numbers", []):
            items.append({"name": f"omits {banned}", "ok": not has_number(text, banned)})

    elif kind == "dates":
        for key, value in check["dates"].items():
            got = answer.get(key) if isinstance(answer, dict) else None
            target = norm_date(value)
            ok = got is not None and target is not None and target in dates_in(text_of(got))
            items.append({"name": key, "ok": ok})

    elif kind == "label":
        def plain(value):
            return " ".join(re.sub(r"[^a-z ]", " ", value.lower()).split())
        joined = plain(text)
        present = [label for label in check["labels"] if plain(label) in joined]
        items.append({"name": check["label"], "ok": present == [check["label"]]})

    elif kind == "shares":
        for name, share in check["shares"].items():
            window = _line_with(text, answer, name)
            items.append({"name": name, "ok": window is not None and has_number(window, share)})

    elif kind == "amounts":
        for name, amount in check["amounts"].items():
            window = _line_with(text, answer, name)
            items.append({"name": name, "ok": window is not None and has_number(window, amount)})

    elif kind == "citation":
        items.append({"name": check["number_label"], "ok": _has_duration(text, check["number"], check["unit"])})
        items.append({"name": check["section"], "ok": has_section(text, check["section"])})

    elif kind == "amount_key":
        got = answer.get(check["key"]) if isinstance(answer, dict) else None
        items.append({"name": check["key"], "ok": got is not None and has_number(text_of(got), check["value"])})

    else:
        raise ValueError(kind)

    failed = [i["name"] for i in items if not i["ok"]]
    return {"ok": not failed, "items": items, "reason": ", ".join(failed)}


WORDS = {
    2: "two", 3: "three", 4: "four", 14: "fourteen", 21: "twenty-one",
    30: "thirty", 120: "one hundred twenty",
}


def _has_duration(text, number, unit):
    lowered = text.lower()
    candidates = [str(number)] + ([WORDS[number]] if number in WORDS else [])
    return any(re.search(rf"(?<![\d-]){re.escape(c)}[\s-]*\(?\d*\)?[\s-]*{unit}", lowered) for c in candidates)


def _line_with(text, answer, name):
    """The part of the reply that belongs to one named person."""
    lowered = name.lower()
    if isinstance(answer, dict):
        for key, value in answer.items():
            if lowered in str(key).lower():
                return text_of(value)
            if isinstance(value, (list, dict)):
                inner = _line_with(text_of(value), value, name)
                if inner is not None:
                    return inner
    if isinstance(answer, list):
        for item in answer:
            if lowered in text_of(item).lower():
                return text_of(item)
        return None
    for line in text.splitlines():
        if lowered in line.lower():
            return line
    return None
