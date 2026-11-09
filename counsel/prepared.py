"""Prepared requests: 12 per kind, generated from a seeded generator.

Every check is written from the values used to generate the document, never from
a model's output. A prepared request is recognized by exact text plus its document.
"""
import hashlib
import random
import re
from datetime import date, timedelta
from pathlib import Path

DEPOSITION_1 = (Path(__file__).parent.parent / "seed" / "deposition_1.txt").read_text()

HARLOW_CASE = "CGC-26-418822"
ROURKE_CASE = "CGC-26-507316"

DEPOSITION_REQUEST = (
    "Summarize this deposition in at most 5 short bullets. Keep every date, time and dollar amount, "
    "and name the person who gave the instruction not to write anything down."
)
DATES_REQUEST = (
    "Pull the dates from this client email. Give each one as an ISO date (YYYY-MM-DD) "
    "under the keys signed_date and due_date."
)
TAG_LABELS = ["Attorney-Client", "Work Product", "Not Privileged"]
TAG_REQUEST = "Tag this document for the privilege log. Answer with exactly one of: Attorney-Client, Work Product, Not Privileged."
INSTRUMENT_REQUEST = (
    "Summarize this instrument in at most 5 short bullets. Keep the date it was signed and both dollar "
    "amounts, and name the executor and the successor trustee."
)
BENEFICIARY_REQUEST = "List every beneficiary and each one's share as a percentage, one per line as name: percent."
DISTRIBUTION_REQUEST = (
    "Compute the dollar amount each beneficiary receives after debts, expenses and the specific bequest. "
    "One line per person as name: amount."
)

LABELS = {
    "summarize_deposition": "Summarize a deposition",
    "extract_dates": "Pull dates from a client email",
    "privilege_tag": "Tag for the privilege log",
    "draft_letter": "Draft a meet-and-confer letter",
    "public_research": "Research",
    "public_deadline": "Public lookup",
    "public_limit": "Public fee or limit",
    "advice": "Advice or a decision",
    "summarize_instrument": "Summarize a will or trust",
    "extract_beneficiaries": "List beneficiaries and shares",
    "compute_distribution": "Compute distributions",
    "draft_client_letter": "Draft a client letter",
    "other": "Other work",
}
RESEARCH_LABEL = {"maya": "Research: civil procedure", "daniel": "Research: probate"}

# (Text is, Stakes) by kind. Stakes set how many passes a row needs.
PATH = {
    "summarize_deposition": ("privileged", "low"),
    "extract_dates": ("privileged", "low"),
    "privilege_tag": ("privileged", "low"),
    "draft_letter": ("privileged", "medium"),
    "public_research": ("public", "medium"),
    "public_deadline": ("public", "medium"),
    "public_limit": ("public", "medium"),
    "advice": ("either", "never"),
    "summarize_instrument": ("privileged", "low"),
    "extract_beneficiaries": ("privileged", "low"),
    "compute_distribution": ("privileged", "medium"),
    "draft_client_letter": ("privileged", "medium"),
    "other": ("either", "medium"),
}
KINDS_BY_USER = {
    "maya": ["summarize_deposition", "extract_dates", "privilege_tag", "draft_letter", "public_deadline", "public_limit", "public_research", "advice"],
    "daniel": [
        "summarize_instrument", "extract_beneficiaries", "compute_distribution",
        "draft_client_letter", "public_deadline", "public_limit", "public_research", "advice",
    ],
}


ALL_KINDS = list(dict.fromkeys(k for kinds in KINDS_BY_USER.values() for k in kinds))


def kinds_for(user):
    """The fictional people have their own task lists. Everyone else can ask for any kind of work."""
    return KINDS_BY_USER.get(user, ALL_KINDS)


def label_for(user, kind):
    if kind == "public_research":
        return RESEARCH_LABEL.get(user, "Research")
    return LABELS.get(kind, kind)


def normalize(text):
    return re.sub(r"\s+", " ", text or "").strip()


def key(text, doc_title):
    return hashlib.sha256(f"{normalize(text)}|{doc_title or ''}".encode()).hexdigest()


def secret(rng):
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "sk-test-" + "".join(rng.choice(alphabet) for _ in range(20))


def money(rng, low, high, step=100):
    return rng.randrange(low, high, step)


def comma(value):
    return f"{value:,}"


def long_date(d, rng=None, style=None):
    style = style if style is not None else (rng.randrange(3) if rng else 0)
    month = d.strftime("%B")
    return {0: f"{d.day} {month}", 1: f"{month} {d.day}", 2: f"{d.day} {d.strftime('%b')}"}[style]


WITNESSES = [
    ("Priya Nair", "Brightline dispatcher"), ("Luis Ortega", "Brightline driver"),
    ("Sam Whitfield", "Brightline yard manager"), ("Dana Kowalski", "Brightline claims adjuster"),
    ("Marcus Bell", "Brightline night supervisor"), ("Irene Fuentes", "Brightline safety officer"),
    ("Owen Tran", "Brightline mechanic"), ("Grace Lindqvist", "Brightline operations lead"),
    ("Theo Banks", "Brightline dispatcher"), ("Nina Sorensen", "Brightline driver"),
    ("Caleb Hart", "Brightline scheduler"),
]
SUPERVISORS = [
    "Karen Doyle", "Victor Stanhope", "Paula Mercer", "Glenn Ashby", "Rosa Delgado", "Howard Finch",
    "Lena Park", "Martin Voss", "Alice Quinn", "Peter Holt", "Joan Ellis",
]
GOODS = ["pears", "apples", "plums", "cherries", "apricots", "nectarines"]
EXCUSES = [
    "the court reporter's laptop wouldn't connect", "the conference room was double booked",
    "the videographer was stuck on the bridge", "the exhibits binder was left at the office",
]
CHATTER = [
    "Lunch ran long. The afternoon was mostly exhibits we already had.",
    "We broke twice for phone calls. The last hour covered background we already knew.",
    "The room was freezing and everyone complained. Most of the afternoon repeated the morning.",
    "Parking validation took forever. The final session added nothing new.",
]
SHIPPERS = ["Harlow Orchards", "Sunvale Foods"]


def _deposition(rng, i):
    witness, role = WITNESSES[i]
    last = witness.split()[-1]
    supervisor = SUPERVISORS[i]
    event = date(2026, rng.randint(6, 9), rng.randint(2, 27))
    hour = rng.randint(0, 4)
    t1 = f"{hour:02d}:{rng.choice([5, 10, 15, 20, 40, 45]):02d}"
    t2 = f"{hour + rng.randint(3, 5):02d}:{rng.choice([0, 30, 50]):02d}"
    theirs = money(rng, 40000, 70000)
    ours = theirs + money(rng, 9000, 24000)
    event_text = long_date(event, rng)
    cases = rng.randint(800, 1600)
    trailer = rng.randint(4000, 4999)
    shipper = rng.choice(SHIPPERS)
    start = f"{rng.randint(9, 10)}:{rng.choice(['05', '20', '40'])}"
    day = rng.randint(1, 3)
    late = rng.choice(["ten", "fifteen", "twenty", "thirty"])
    body = (
        f"PRIVILEGED & CONFIDENTIAL · ATTORNEY WORK PRODUCT\n"
        f"Harlow Orchards v. Brightline Freight, {HARLOW_CASE}\n"
        f"Deposition of {witness} ({role}), Day {day}. Notes by M. Chen.\n\n"
        f"Started at {start}, {late} minutes late because {rng.choice(EXCUSES)}. "
        f"Opposing counsel (Alan Pierce) objected to form on nearly every question. None of it matters.\n\n"
        f"{last} admitted the refrigeration unit on trailer {trailer} showed a temperature alarm at {t1} on "
        f"{event_text}, and that nobody on the night shift acknowledged it until {t2}. "
        f"The witness said the alarm log \"gets ignored a lot\" because of false alarms.\n\n"
        f"{last} confirmed Brightline's policy requires a driver call within 30 minutes of any alarm, "
        f"and could not name anyone who made that call.\n\n"
        f"{last} estimated the load at {comma(cases)} cases of {rng.choice(GOODS)} for {shipper}, and said "
        f"Brightline's claims team valued the loss at {comma(theirs)}. Ours is {comma(ours)}. "
        f"Flag for the damages expert.\n\n"
        f"On the email chain, {last} said the supervisor, {supervisor}, told the witness \"don't write anything down about the alarm.\" "
        f"Pierce instructed the witness not to answer follow-ups. We should move to compel.\n\n"
        f"{rng.choice(CHATTER)}\n\n"
        f"Follow-ups: send the errata reminder, ask Ruth whether to notice {supervisor}'s deposition, and get the "
        f"alarm log in native format. Reporter portal login: {secret(rng)}. "
        f"Reporter contact: depo@baysidereporting.com, (415) 555-0187.\n"
    )
    check = {
        "type": "facts", "max_ratio": 0.45,
        "facts": [
            {"type": "date", "value": event_text}, {"type": "time", "value": t2},
            {"type": "number", "value": str(theirs)}, {"type": "number", "value": str(ours)},
            {"type": "text", "value": supervisor},
        ],
    }
    return f"{last} deposition, Day {day}", body, check


FIRST_NAMES = ["Elena", "Jonas", "Ravi", "Mei", "Olu", "Sofia", "Tariq", "Hannah", "Diego", "Noor", "Felix", "Ana"]
CLIENT_CONTACTS = [f"{name}, Sunvale Foods" for name in FIRST_NAMES[:4]] + \
    [f"{name}, Tidewell Insurance" for name in FIRST_NAMES[4:8]] + \
    [f"{name}, Harlow Orchards" for name in FIRST_NAMES[8:]]
LEASE_THINGS = [("lease", "deposit"), ("supply agreement", "first invoice"), ("storage contract", "retainer")]


def _email(rng, i):
    contact = CLIENT_CONTACTS[i]
    thing, payment = LEASE_THINGS[i % 3]
    signed = date(2026, rng.randint(1, 6), rng.randint(2, 27))
    due = signed + timedelta(days=rng.randint(10, 60))
    if i % 3 == 0:
        statement = f"The {thing} was signed on {signed.isoformat()}. The {payment} is due on {due.isoformat()}."
    elif i % 3 == 1:
        statement = (
            f"We signed the {thing} on {signed.day} {signed.strftime('%B')} {signed.year}. "
            f"The {payment} is due on {due.strftime('%B')} {due.day}, {due.year}."
        )
    else:
        statement = f"Signed date for the {thing}: {signed.isoformat()}. Payment date for the {payment}: {due.isoformat()}."
    body = (
        f"PRIVILEGED & CONFIDENTIAL · ATTORNEY-CLIENT COMMUNICATION\n"
        f"From: {contact}\nTo: Maya Chen\nSubject: dates for the file\n\n"
        f"Hi Maya, thanks for your time on the phone. {statement} "
        f"Please keep this between us while we work out how to approach Brightline Freight.\n\nThanks,\n{contact.split(',')[0]}\n"
    )
    check = {"type": "dates", "dates": {"signed_date": signed.isoformat(), "due_date": due.isoformat()}}
    return f"Client email {i + 1}: {contact.split(', ')[1]}", body, check


TAG_TEMPLATES = {
    "Attorney-Client": [
        "From: {person}, Harlow Orchards\nTo: Maya Chen\n\nMaya, I need your legal advice on whether we have to tell our insurer about the {item} before the mediation. Please treat this as confidential.",
        "From: Maya Chen\nTo: {person}, Sunvale Foods\n\nYou asked for our legal advice about the {item}. In my opinion you should not respond to Brightline directly. This is a confidential communication between lawyer and client.",
    ],
    "Work Product": [
        "ATTORNEY NOTES, prepared for trial. Prepared by M. Chen in anticipation of litigation. My assessment of {person}'s credibility: weak on the {item}. Our theory should focus on the alarm log.",
        "Litigation memo prepared by counsel for the upcoming trial. Mental impressions on the {item}: {person} will be a difficult witness. Draft cross-examination outline to follow.",
    ],
    "Not Privileged": [
        "Bill of lading no. {num}. Shipper: Harlow Orchards. Carrier: Brightline Freight. Contents: {item}. Signed at delivery by {person}. Copy provided to both parties in the ordinary course of business.",
        "Press release from Brightline Freight: the company announced a new route and named {person} as regional director. Contents reference the {item}. Published on the company website.",
    ],
}
TAG_ITEMS = ["pear shipment", "alarm log", "temperature report", "trailer lease"]


def _tag_doc(rng, i):
    label = TAG_LABELS[i % 3]
    template = TAG_TEMPLATES[label][(i // 3) % 2]
    body = template.format(person=WITNESSES[i % len(WITNESSES)][0], item=rng.choice(TAG_ITEMS), num=rng.randint(10000, 99999)) + "\n"
    return f"File item {i + 1:02d}", body, {"type": "label", "label": label, "labels": TAG_LABELS}


DISCOVERY_ITEMS = [
    "maintenance records for the reefer units", "alarm logs", "driver call records", "dispatch emails",
    "claims team valuation file", "trailer inspection reports", "night shift rosters", "training manuals",
    "incident reports", "insurance correspondence", "route sheets", "temperature probe data",
]


def _letter(rng, i):
    item = DISCOVERY_ITEMS[i]
    served = date(2026, rng.randint(3, 8), rng.randint(2, 27))
    deadline = served + timedelta(days=rng.randint(30, 45))
    walk = money(rng, 30000, 60000)
    served_text = long_date(served, style=0)
    deadline_text = long_date(deadline, style=0)
    body = (
        f"PRIVILEGED & CONFIDENTIAL · ATTORNEY NOTES\nHarlow Orchards v. Brightline Freight, {HARLOW_CASE}\n\n"
        f"Requests for production served on Alan Pierce on {served_text}. Responses covering the {item} were due "
        f"on {deadline_text}. Nothing received.\n\n"
        f"STRATEGY (internal only): our walk-away number is {comma(walk)}. Pierce is bluffing about a cross-claim, "
        f"and we should not reveal we already hold copies from the insurer.\n"
    )
    request = (
        f"Draft a meet-and-confer letter to Alan Pierce about the overdue {item}. State the case number, the date the "
        f"requests were served and the date responses were due. Do not include anything from the strategy notes."
    )
    check = {
        "type": "facts",
        "facts": [
            {"type": "text", "value": HARLOW_CASE}, {"type": "date", "value": served_text},
            {"type": "date", "value": deadline_text},
        ],
        "forbid": ["walk-away", "bluffing", "cross-claim", "from the insurer"],
        "forbid_numbers": [str(walk)],
    }
    return f"Discovery notes: {item}", body, request, check


RESEARCH_MAYA = [
    (("For Harlow Orchards' claim, what is the California time limit for breach of a written contract?",
      "What is the California statute of limitations for breach of a written contract?",
      "How long does a party have in California to sue for breach of a written contract?"),
     {"type": "citation", "number": 4, "unit": "year", "number_label": "4 years", "section": "337"}),
    (("What is the California statute of limitations for breach of an oral contract?",
      "For Sunvale Foods' dispute, what is the California limit for breach of an oral contract?"),
     {"type": "citation", "number": 2, "unit": "year", "number_label": "2 years", "section": "339"}),
    (("What is the California statute of limitations for fraud?",
      "How long does a California plaintiff have to sue for fraud?"),
     {"type": "citation", "number": 3, "unit": "year", "number_label": "3 years", "section": "338(d)"}),
    (("What is the California statute of limitations for personal injury?",
      "How long does a California plaintiff have to file a personal injury suit?"),
     {"type": "citation", "number": 2, "unit": "year", "number_label": "2 years", "section": "335.1"}),
    (("How many days does a defendant have to answer a federal complaint after service?",
      "For Tidewell Insurance's case, how long after service is an answer due on a federal complaint?"),
     {"type": "citation", "number": 21, "unit": "day", "number_label": "21 days", "section": "12(a)"}),
    (("How long does a defendant have to remove a case to federal court?",),
     {"type": "citation", "number": 30, "unit": "day", "number_label": "30 days", "section": "1446(b)"}),
    (("How many days after the Rule 26(f) conference are initial disclosures due?",
      "When are initial disclosures due after the Rule 26(f) conference?"),
     {"type": "citation", "number": 14, "unit": "day", "number_label": "14 days", "section": "26(a)(1)(C)"}),
]
RESEARCH_DANIEL = [
    (("How long after a will is admitted to probate can it be contested in California?",
      "What is the deadline in California to contest a will after probate?",
      "For Helen Rourke's estate, how long does someone have to contest a will after it is admitted to probate in California?",
      "What is the California time limit on a will contest once probate is granted?",
      "How many days after probate can a California will be contested?",
      "For the Rourke Family Trust's planning, what is the California will contest window after probate?"),
     {"type": "citation", "number": 120, "unit": "day", "number_label": "120 days", "section": "8270"}),
    (("How long does a creditor have to file a claim after letters issue in California probate?",
      "What is the California deadline for a creditor claim after letters issue?",
      "For Helen Rourke's estate, how long do creditors have to file after letters issue in California?",
      "When must a creditor file a claim in a California probate after letters issue?",
      "How many months does a California creditor have to claim against an estate after letters issue?",
      "For Pinecrest Labs' unpaid invoice, how long does a creditor have after letters issue in California?"),
     {"type": "citation", "number": 4, "unit": "month", "number_label": "4 months", "section": "9100"}),
]
RESEARCH_SUFFIX = " Give the number and the section."

ADVICE = {
    "maya": [
        "Should we accept Brightline's offer?", "Should Harlow Orchards settle before the mediation?",
        "Should the client waive privilege on the alarm log memo?", "Should we move to compel or wait?",
        "Do you think we should notice Karen Doyle's deposition?", "Should the client sign the tolling agreement?",
        "Should we tell the client to reject the counteroffer?", "Is it worth taking this case to trial?",
        "Should we drop the claim against the insurer?", "Should the client respond to Brightline directly?",
        "Should we accept the mediator's proposal?", "Should we waive the jury?",
    ],
    "daniel": [
        "Should the estate accept the buyout offer?", "Should Helen Rourke contest the trust amendment?",
        "Should the executor pay this creditor claim?", "Should we advise the family to settle with the nephew?",
        "Should the trustee sell the house now?", "Should the estate waive the accounting?",
        "Should the client disclaim the inheritance?", "Should we recommend removing the trustee?",
        "Should the estate go to mediation?", "Should the executor resign?",
        "Should Helen Rourke sign the release?", "Should the trust accept the Pinecrest Labs offer?",
    ],
}

PEOPLE_ROURKE = [
    "Thomas Rourke", "Clara Rourke", "Alma Rourke", "Benedict Rourke", "Ivy Rourke", "Julian Rourke",
    "Fiona Hale", "Marcus Hale", "Tessa Lang", "Arthur Lang", "Nora Vance", "Silas Vance",
]
EXECUTORS = ["Helen Rourke", "Patrick Moss", "Lydia Grant", "Owen Keane", "Clara Ng", "Simon Abara"]
TRUSTEES = ["Margaret Oyelaran", "Paul Sandoval", "Rina Kapoor", "George Whitlock", "Amy Forsythe", "Isaac Levin"]
FILLER = [
    "The witnesses signed in the presence of each other at the family's kitchen table on a rainy afternoon.",
    "The notary arrived late and stayed for coffee, which everyone agreed was unnecessary.",
    "Earlier drafts are in the blue folder and should not be relied on for anything.",
    "The family dog was present throughout and is not a beneficiary of this instrument.",
]


def _instrument(rng, i):
    executor = EXECUTORS[i % 6]
    trustee = TRUSTEES[(i + 2) % 6]
    signed = date(2025, rng.randint(1, 12), rng.randint(2, 27))
    bequest = money(rng, 15000, 60000, 500)
    funding = money(rng, 150000, 600000, 1000)
    kind = "Last Will and Testament" if i % 2 == 0 else "Declaration of Trust"
    signed_text = long_date(signed, style=0) + f" {signed.year}"
    body = (
        f"PRIVILEGED & CONFIDENTIAL · ATTORNEY WORK PRODUCT\nEstate of Rourke, {ROURKE_CASE}\n"
        f"{kind} of Helen Rourke, abstract {i + 1}. Notes by D. Osei.\n\n"
        f"This instrument was signed on {signed_text}. {rng.choice(FILLER)} It revokes all earlier wills and codicils, "
        f"which the family says were kept in three different drawers.\n\n"
        f"It names {executor} as executor, with authority to act without bond. It provides a specific bequest of "
        f"{comma(bequest)} to the local library, payable within one year of death.\n\n"
        f"It funds the Rourke Family Trust with {comma(funding)} in brokerage assets and names {trustee} as successor "
        f"trustee if the first trustee cannot serve. The trust pays income to the surviving spouse for life.\n\n"
        f"{rng.choice(FILLER)} We spent most of the meeting on who would keep the piano, which is not addressed in "
        f"the instrument at all, and on a long story about a boat. None of that belongs in the file.\n\n"
        f"Follow-ups: confirm the brokerage statements, ask Ruth about the bond waiver, and call the bank. "
        f"Portal login for the bank: {secret(rng)}. Family contact: helen.rourke@example.com, (415) 555-0142.\n"
    )
    check = {
        "type": "facts", "max_ratio": 0.45,
        "facts": [
            {"type": "date", "value": signed_text}, {"type": "number", "value": str(bequest)},
            {"type": "number", "value": str(funding)}, {"type": "text", "value": executor},
            {"type": "text", "value": trustee},
        ],
    }
    return f"Rourke {kind.split()[-1].lower()} abstract {i + 1}", body, check


SHARE_SPLITS = [(50, 30, 20), (40, 40, 20), (60, 25, 15), (45, 35, 20), (50, 25, 25), (70, 20, 10)]


def _beneficiaries(rng, i):
    people = rng.sample(PEOPLE_ROURKE, 3)
    shares = SHARE_SPLITS[i % 6]
    lines = "\n".join(f"Article {n + 4}. To {p}, {s} percent of the residue." for n, (p, s) in enumerate(zip(people, shares)))
    body = (
        f"PRIVILEGED & CONFIDENTIAL\nEstate of Rourke, {ROURKE_CASE}\nDispositive provisions, extract {i + 1}.\n\n"
        f"Article 1 appoints the executor. Article 2 directs payment of debts. Article 3 confirms the household gifts.\n"
        f"{lines}\nArticle 7 covers lapse. If a beneficiary does not survive by 30 days, the share passes to the others.\n"
    )
    return f"Rourke dispositive extract {i + 1}", body, {"type": "shares", "shares": dict(zip(people, shares))}


def _distribution(rng, i):
    people = rng.sample(PEOPLE_ROURKE, 3)
    shares = SHARE_SPLITS[i % 6]
    gross = money(rng, 400000, 900000, 5000)
    debts = money(rng, 20000, 60000, 500)
    bequest = money(rng, 10000, 40000, 1000)
    bequest_to = people[-1]
    residue = gross - debts - bequest
    amounts = {p: residue * s / 100 for p, s in zip(people, shares)}
    amounts[bequest_to] += bequest
    body = (
        f"PRIVILEGED & CONFIDENTIAL\nEstate of Rourke, {ROURKE_CASE}\nDistribution worksheet {i + 1}.\n\n"
        f"Gross estate: {comma(gross)}. Debts and administration expenses: {comma(debts)}. "
        f"Specific bequest of {comma(bequest)} to {bequest_to}, paid first and in addition to any share of the residue.\n"
        f"Residue after debts, expenses and the bequest is divided: "
        + ", ".join(f"{p} {s} percent" for p, s in zip(people, shares)) + ".\n"
    )
    check = {"type": "amounts", "amounts": {p: (int(v) if v == int(v) else round(v, 2)) for p, v in amounts.items()}}
    return f"Distribution worksheet {i + 1}", body, check


def _client_letter(rng, i):
    executor = EXECUTORS[i % 6]
    hearing = date(2026, rng.randint(9, 12), rng.randint(2, 27))
    first = money(rng, 20000, 90000, 500)
    hearing_text = long_date(hearing, style=0)
    body = (
        f"PRIVILEGED & CONFIDENTIAL · ATTORNEY NOTES\nEstate of Rourke, {ROURKE_CASE}\n\n"
        f"Hearing on the petition for preliminary distribution is set for {hearing_text}. The first distribution "
        f"will be {comma(first)} if granted. {executor} is the executor and has signed the petition.\n"
        f"Internal: the nephew may object; do not mention this to the client yet.\n"
    )
    request = (
        "Draft a letter to the client, Helen Rourke, about the preliminary distribution. State the hearing date, "
        "the amount of the first distribution and the name of the executor. Do not mention anything marked internal."
    )
    check = {
        "type": "facts",
        "facts": [
            {"type": "date", "value": hearing_text}, {"type": "number", "value": str(first)},
            {"type": "text", "value": executor},
        ],
        "forbid": ["nephew"],
    }
    return f"Preliminary distribution notes {i + 1}", body, request, check


DOCKET_PARTIES = [
    "Harlow Orchards v. Brightline Freight", "Alder Logistics v. Merced Packing",
    "Sunvale Foods v. Coastline Cold Storage", "Redwood Haulers v. Tidewell Insurance",
]


def _nice(d):
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def _docket_deadline(rng, i):
    """Maya's public deadline: printed on the docket, so it only has to be read."""
    hearing, dept = date(2026, rng.randint(9, 12), rng.randint(1, 27)), rng.randint(301, 620)
    party = DOCKET_PARTIES[i % len(DOCKET_PARTIES)]
    text = (
        "Read this public docket entry. Give the hearing date and the department.\n\n"
        f"SUPERIOR COURT OF CALIFORNIA, COUNTY OF SAN FRANCISCO. Public docket. {party}, CGC-26-{rng.randint(100000, 999999)}. "
        f"Notice of motion filed {_nice(hearing - timedelta(days=30))}. Motion to compel set for hearing on {_nice(hearing)} "
        f"at 9:00 a.m. in Department {dept}. Check the court website for changes."
    )
    return text, {"type": "facts", "facts": [{"type": "date", "value": hearing.isoformat()}, {"type": "number", "value": str(dept)}]}


AFR_TERMS = ["Short-term", "Mid-term", "Long-term"]
AFR_LEVELS = ["AFR", "110% AFR", "120% AFR", "130% AFR"]
AFR_PERIODS = ["Annual", "Semiannual", "Quarterly", "Monthly"]


def _rate_lookup(rng, i):
    """Daniel's public lookup: the IRS rate table, laid out as published, with terms as section headings."""
    values = iter(rng.sample(range(300, 620), len(AFR_TERMS) * len(AFR_LEVELS) * len(AFR_PERIODS)))
    table, lines = {}, ["Rate | " + " | ".join(AFR_PERIODS)]
    for term in AFR_TERMS:
        lines.append(term)
        for level in AFR_LEVELS:
            cells = {period: next(values) / 100 for period in AFR_PERIODS}
            table[(term, level)] = cells
            lines.append(f"{level} | " + " | ".join(f"{cells[p]:.2f}%" for p in AFR_PERIODS))
    term, level, period = rng.choice(AFR_TERMS), rng.choice(AFR_LEVELS), rng.choice(AFR_PERIODS)
    answer = table[(term, level)][period]
    text = (
        f"Read this public IRS table of applicable federal rates. Give only the {term} {level} rate, {period} compounding.\n\n"
        + "\n".join(lines)
    )
    others = [str(v) for cells in table.values() for v in cells.values() if v != answer]
    return text, {"type": "facts", "facts": [{"type": "number", "value": str(answer)}], "forbid_numbers": others}


def _limit_check(value, limit):
    """Maya's public fee or limit: one comparison against a stated limit."""
    text = (
        f"A public rule says limited civil cases cover claims up to {limit:,} dollars. A claim is for {value:,} dollars. "
        "Is it within the limit? Answer with exactly one of: Within, Over."
    )
    return text, {"type": "label", "label": "Within" if value <= limit else "Over", "labels": ["Within", "Over"]}


def _statutory_fee(value):
    """Daniel's public fee or limit: tiered arithmetic on a published schedule."""
    fee = min(value, 100000) * 0.04 + min(max(value - 100000, 0), 100000) * 0.03 + max(value - 200000, 0) * 0.02
    text = (
        "The public statutory fee schedule pays an executor 4 percent of the first 100,000, 3 percent of the next 100,000 "
        f"and 2 percent of the next 800,000. For an estate of {value:,}, what is the fee in dollars?"
    )
    return text, {"type": "facts", "facts": [{"type": "number", "value": str(int(fee))}]}


def build():
    """Return {"docs": [...], "requests": [...]}. Deterministic: seeded at 7."""
    rng = random.Random(7)
    docs, requests = [], []

    def add(user, kind, text, title, body, check, matter, listed=True, source="prepared", privileged=True):
        if title is not None:
            docs.append({"matter": matter, "title": title, "body": body, "privileged": privileged, "listed": listed})
        requests.append({
            "id": f"{user}-{kind}-{sum(1 for r in requests if r['user'] == user and r['kind'] == kind and r['source'] == source):02d}"
                  ,
            "user": user, "kind": kind, "text": text, "doc_title": title, "check": check,
            "source": source, "doc_len": len(body) if body else None,
        })

    add("maya", "summarize_deposition", DEPOSITION_REQUEST, "Reyes deposition, Day 2", DEPOSITION_1, {
        "type": "facts", "max_ratio": 0.45,
        "facts": [
            {"type": "date", "value": "14 August"}, {"type": "time", "value": "06:30"},
            {"type": "number", "value": "61400"}, {"type": "number", "value": "74900"},
            {"type": "text", "value": "Karen Doyle"},
        ],
    }, "harlow")
    for i in range(11):
        title, body, check = _deposition(rng, i)
        add("maya", "summarize_deposition", DEPOSITION_REQUEST, title, body, check, "harlow")
    for i in range(12):
        title, body, check = _email(rng, i)
        add("maya", "extract_dates", DATES_REQUEST, title, body, check, "harlow")
    for i in range(12):
        title, body, check = _tag_doc(rng, i)
        add("maya", "privilege_tag", TAG_REQUEST, title, body, check, "harlow")
    for i in range(12):
        title, body, request, check = _letter(rng, i)
        add("maya", "draft_letter", request, title, body, check, "harlow")
    for i in range(12):
        topic = RESEARCH_MAYA[i % len(RESEARCH_MAYA)]
        wording = topic[0][(i // len(RESEARCH_MAYA)) % len(topic[0])]
        add("maya", "public_research", wording + RESEARCH_SUFFIX, None, None, topic[1], "harlow")
    for text in ADVICE["maya"]:
        add("maya", "advice", text, None, None, None, "harlow")

    for i in range(12):
        title, body, check = _instrument(rng, i)
        add("daniel", "summarize_instrument", INSTRUMENT_REQUEST, title, body, check, "rourke")
    for i in range(12):
        title, body, check = _beneficiaries(rng, i)
        add("daniel", "extract_beneficiaries", BENEFICIARY_REQUEST, title, body, check, "rourke")
    for i in range(12):
        title, body, check = _distribution(rng, i)
        add("daniel", "compute_distribution", DISTRIBUTION_REQUEST, title, body, check, "rourke")
    for i in range(12):
        title, body, request, check = _client_letter(rng, i)
        add("daniel", "draft_client_letter", request, title, body, check, "rourke")
    for i in range(12):
        topic = RESEARCH_DANIEL[i % 2]
        wording = topic[0][(i // 2) % len(topic[0])]
        add("daniel", "public_research", wording + RESEARCH_SUFFIX, None, None, topic[1], "rourke")
    for text in ADVICE["daniel"]:
        add("daniel", "advice", text, None, None, None, "rourke")

    # Public tasks with the same name for both people. The work differs by practice. Own generator, so earlier fixtures don't shift.
    public = random.Random(23)
    limits = public.sample(range(1000, 90000, 500), 12)
    fees = public.sample(range(150000, 950000, 5000), 12)
    for i in range(12):
        text, check = _docket_deadline(public, i)
        add("maya", "public_deadline", text, None, None, check, "harlow")
        text, check = _limit_check(limits[i], 35000 if i % 2 else 12500)
        add("maya", "public_limit", text, None, None, check, "harlow")
        text, check = _rate_lookup(public, i)
        add("daniel", "public_deadline", text, None, None, check, "rourke")
        text, check = _statutory_fee(fees[i])
        add("daniel", "public_limit", text, None, None, check, "rourke")

    return {"docs": docs, "requests": requests}


_cache = None


def catalog():
    global _cache
    if _cache is None:
        data = build()
        by_key = {key(r["text"], r["doc_title"]): r for r in data["requests"]}
        by_id = {r["id"]: r for r in data["requests"]}
        _cache = {**data, "by_key": by_key, "by_id": by_id}
    return _cache


def for_user(user, kind, source="prepared"):
    return [r for r in catalog()["requests"] if r["user"] == user and r["kind"] == kind and r["source"] == source]


def match(text, doc_title):
    return catalog()["by_key"].get(key(text, doc_title))

