"""Prompts for the box. Built only from the requesting person's own material; stateless."""
from . import prepared

SHAPE_TEXT = 'Reply with one JSON object and nothing else: {"answer": "<your answer as text>", "actions": []}. Put no working or notes outside the JSON.'
SHAPE_DATES = 'Reply with one JSON object and nothing else, with a comma after the answer: {"answer": {"<key>": "YYYY-MM-DD", "<key>": "YYYY-MM-DD"}, "actions": []}.'
BASE = "You are an assistant at a small law firm. Use only the material given to you. "
RESEARCH_BASE = "You are an assistant at a small law firm. "

BY_KIND = {
    "extract_dates": "Give each requested key its date as YYYY-MM-DD. Work out dates that are described rather than stated.",
    "privilege_tag": (
        "The answer is exactly one of the listed labels and nothing else. Attorney-Client means a confidential message between a "
        "lawyer and a client seeking or giving legal advice. Work Product means notes or memos counsel prepared for litigation. "
        "Not Privileged means an ordinary business record or a public document."
    ),
    "draft_letter": "The answer is the letter as text. Include every item the request names. Never use anything from strategy or internal notes.",
    "draft_client_letter": "The answer is the letter as text. Include every item the request names. Never use anything marked internal.",
    "extract_beneficiaries": 'The answer is text with one line per person, written as "name: percent".',
    "compute_distribution": 'The answer is text with one line per person, written as "name: amount". Do the arithmetic.',
    "public_research": "Answer from your knowledge of United States law. State only the time limit and the section, in under 15 words. If unsure, give your best single guess.",
}
SUMMARIES = ("summarize_deposition", "summarize_instrument")


def max_tokens(kind):
    """A research shadow is one sentence; left at 900 it rambles for 14 seconds and fails the same way."""
    return 200 if kind == "public_research" else None


def summary_limit(doc_len):
    """Tell the model a target inside the 45% check; the check itself never changes."""
    return int(doc_len * 0.45 * 0.8)


def build(kind, text, docs):
    """docs: [(title, body)] already cleared by the walls. Returns (system, user)."""
    parts = [RESEARCH_BASE if kind == "public_research" else BASE]
    if kind in SUMMARIES and docs:
        limit = summary_limit(sum(len(body) for _, body in docs))
        parts.append(
            f"The summary must be under {limit} characters in total. Each bullet is one short line of facts. "
            "Leave out logistics, objections, lunch, contact details and follow-up tasks. Write numbers exactly as they appear. "
            "Put the bullets in one string separated by newlines. "
        )
    if kind in BY_KIND:
        parts.append(BY_KIND[kind] + " ")
    parts.append(SHAPE_DATES if kind == "extract_dates" else SHAPE_TEXT)
    user = text
    for title, body in docs:
        user += f"\n\nDOCUMENT ({title}):\n{body}"
    return "".join(parts), user


def label_set(user):
    return prepared.KINDS_BY_USER.get(user, [])
