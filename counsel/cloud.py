"""The only way out of the building. Everything that reaches the cloud passes through send()."""
import json
import threading

from . import db, llm, masking

_slots = threading.BoundedSemaphore(3)

SYSTEM = (
    "You answer public legal research questions for a small law firm. Be brief and exact. State the number and the "
    'section. Reply with one JSON object and nothing else: {"answer": <your answer as text>, "actions": []}.'
)


class Blocked(Exception):
    """Masking broke. The call did not happen."""


def send(request_id, user_id, text, find_people=None):
    """Mask, log the exact payload, call, restore. Returns a dict for the request row."""
    try:
        masked, key, tags = masking.mask(text, find_people=find_people)
    except masking.MaskError as e:
        raise Blocked(str(e)) from e
    system = SYSTEM + (" " + masking.NOTE if tags else "")
    payload_id = db.run(
        "INSERT INTO cloud_payloads (request_id, ts, user, system, user_text, tags) VALUES (?,?,?,?,?,?)",
        request_id, db.now(), user_id, system, masked, json.dumps(tags),
    )
    with _slots:
        raw, ms = llm.cloud_chat(system, masked)
    parsed = llm.first_json(raw)
    answer_with_tags = parsed.get("answer") if parsed else None
    if answer_with_tags is None:
        answer_with_tags = raw
    if not isinstance(answer_with_tags, str):
        answer_with_tags = json.dumps(answer_with_tags)
    answer, notes = masking.restore(answer_with_tags, key)
    return {
        "cloud_in": masked, "cloud_out_tags": answer_with_tags, "cloud_out": answer, "cloud_ms": ms,
        "keymap": key, "notes": notes, "payload_id": payload_id, "tag_count": len(tags),
        "tags": tags, "parsed": parsed,
    }
