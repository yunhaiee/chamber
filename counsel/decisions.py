"""d1 on the box: privileged?, needs a lawyer?, which kind of work?"""
from . import llm

CRITERIA = {
    "summarize_deposition": "Summarize deposition notes or a transcript",
    "extract_dates": "Pull specific dates out of a client email or document",
    "privilege_tag": "Label a document for a privilege log",
    "draft_letter": "Draft a meet-and-confer or discovery letter to opposing counsel",
    "public_research": "Look up a public legal rule, deadline, statute or code section",
    "public_deadline": "Find or work out a date from a public docket, notice or rule",
    "public_limit": "Check a public fee schedule or monetary limit",
    "advice": "Ask for a legal decision or recommendation about what someone should do",
    "summarize_instrument": "Summarize a will, trust or estate instrument",
    "extract_beneficiaries": "List the beneficiaries and shares named in a will or trust",
    "compute_distribution": "Work out the dollar amounts each beneficiary receives",
    "draft_client_letter": "Draft a letter to a client",
}
PRIVILEGED_Q = (
    "Does this contain confidential client facts, attorney-client communications, attorney notes or work product? "
    "Quoting a public statute or case does not count."
)
JUDGMENT_Q = (
    "Is the person asking for a legal judgment or decision a lawyer must make, such as whether to settle, "
    "whether a client should act, or whether to waive privilege? "
    "Asking to summarize, extract, format, draft or look up the law does not count."
)
STATE_LIMIT = 8000


def state_for(text, docs):
    """The request plus the first 8,000 characters of any attached document."""
    state = text
    body = "\n\n".join(b for _, b in docs)
    if body:
        state += "\n\nATTACHED DOCUMENT:\n" + body[:STATE_LIMIT]
    return state


def questions(kinds):
    return {
        "privileged": {"type": "noul", "instructions": PRIVILEGED_Q},
        "judgment": {"type": "noul", "instructions": JUDGMENT_Q},
        "kind": {
            "type": "choice",
            "instructions": "Which kind of work is being requested?",
            "criteria": {k: CRITERIA[k] for k in kinds},
        },
    }


def ask(kinds, text, docs):
    """Returns {"privileged", "judgment", "kind", "kind_confidence", "ms"} or None if d1 failed."""
    try:
        answers, ms = llm.d1_decide(state_for(text, docs), questions(kinds))
        return {
            "privileged": round(answers["privileged"]["noul"], 3),
            "judgment": round(answers["judgment"]["noul"], 3),
            "kind": answers["kind"]["choice"],
            "kind_confidence": round(answers["kind"]["confidence"], 3),
            "ms": ms,
        }
    except (llm.LocalError, KeyError, TypeError):
        return None
