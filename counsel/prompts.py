"""Prompts for the box. Built only from the requesting person's own material; stateless."""
from . import prepared

SHAPE = 'Reply with one JSON object and nothing else: {"answer": <your answer>, "actions": []}.'
BASE = "You are an assistant at a small law firm. Use only the material given to you. "

BY_KIND = {
    "extract_dates": 'The answer is a JSON object mapping each requested key to its date as YYYY-MM-DD. Work out dates that are described rather than stated.',
    "privilege_tag": "The answer is exactly one of the listed labels and nothing else.",
    "draft_letter": "The answer is the letter as text. Include every item the request names. Never use anything from strategy or internal notes.",
    "draft_client_letter": "The answer is the letter as text. Include every item the request names. Never use anything marked internal.",
    "extract_beneficiaries": 'The answer is text with one line per person, written as "name: percent".',
    "compute_distribution": 'The answer is text with one line per person, written as "name: amount". Do the arithmetic.',
    "public_research": "Answer from your knowledge of United States law. State the number and the section.",
}
SUMMARIES = ("summarize_deposition", "summarize_instrument")


def summary_limit(doc_len):
    """Tell the model a target inside the 45% check; the check itself never changes."""
    return int(doc_len * 0.45 * 0.8)


def build(kind, text, docs):
    """docs: [(title, body)] already cleared by the walls. Returns (system, user)."""
    parts = [BASE]
    if kind in SUMMARIES and docs:
        limit = summary_limit(sum(len(body) for _, body in docs))
        parts.append(
            f"The summary must be under {limit} characters in total. Each bullet is one short line of facts. "
            "Leave out logistics, objections, lunch, contact details and follow-up tasks. Write numbers exactly as they appear. "
        )
    if kind in BY_KIND:
        parts.append(BY_KIND[kind] + " ")
    parts.append(SHAPE)
    user = text
    for title, body in docs:
        user += f"\n\nDOCUMENT ({title}):\n{body}"
    return "".join(parts), user


def label_set(user):
    return prepared.KINDS_BY_USER.get(user, [])
