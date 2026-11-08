"""Row states. Each person, kind and local model has one state, always written as a word."""
import threading

from . import audit, db, llm, prepared

TRIALS = 3
REQUIRED = {"low": TRIALS, "medium": TRIALS}
_lock = threading.Lock()

COLUMN = {"LOCAL": "box", "PROVEN": "box", "SHADOW": "claude", "CLAUDE": "claude", "LAWYER": "lawyer"}
DISPLAY = {"LOCAL": "ON DEVICE", "CLAUDE": "CLOUD", "LAWYER": "HUMAN"}


def model():
    return llm.LOCAL_MODEL


def _stakes(kind):
    return prepared.PATH.get(kind, ("either", "medium"))[1]


def required(kind):
    return REQUIRED.get(_stakes(kind), 8)


def current(user, kind):
    row = db.one("SELECT to_state FROM row_events WHERE user=? AND kind=? AND model=? ORDER BY id DESC LIMIT 1", user, kind, model())
    return row["to_state"] if row else None


def ensure(user, kind, path):
    """A row appears on its first request. path: 'privileged' or 'public'."""
    with _lock:
        state = current(user, kind)
        if state:
            return state
        if prepared.PATH.get(kind, ("", ""))[1] == "never":
            state = "LAWYER"
        else:
            state = "SHADOW" if path == "public" else "LOCAL"
        db.run("INSERT INTO row_events (user, kind, model, from_state, to_state, reason, ts) VALUES (?,?,?,?,?,?,?)",
               user, kind, model(), None, state, "first request", db.now())
        return state


def _live(user, kind):
    return db.all("SELECT * FROM evidence WHERE user=? AND kind=? AND model=? AND cleared=0 ORDER BY id", user, kind, model())


def streak(user, kind):
    n = 0
    for row in reversed(_live(user, kind)):
        if not row["passed"]:
            break
        n += 1
    return n


def word(user, kind, state=None):
    state = state or current(user, kind)
    if state == "SHADOW":
        return f"SHADOW {min(streak(user, kind), required(kind))}/{required(kind)}"
    return DISPLAY.get(state, state)


def origin(user, kind):
    row = db.one("SELECT to_state FROM row_events WHERE user=? AND kind=? AND model=? ORDER BY id LIMIT 1", user, kind, model())
    return row["to_state"] if row else None


def _matter_name(user):
    row = db.one("SELECT m.name FROM matters m JOIN memberships s ON s.matter = m.id WHERE s.user=? LIMIT 1", user)
    return row["name"] if row else ""


def _move(user, kind, from_state, to_state, reason, sentence):
    db.run("INSERT INTO row_events (user, kind, model, from_state, to_state, reason, ts) VALUES (?,?,?,?,?,?,?)",
           user, kind, model(), from_state, to_state, reason, db.now())
    audit.append(user, "row.move", None, sentence)


def record(user, kind, passed, request_id):
    """Add one result for public work and move the row. Privileged work is simply produced."""
    with _lock:
        state = current(user, kind)
        if state not in ("SHADOW", "CLAUDE", "PROVEN"):
            return
        db.run("INSERT INTO evidence (user, kind, model, passed, request_id, ts) VALUES (?,?,?,?,?,?)",
               user, kind, model(), int(passed), request_id, db.now())
        live = _live(user, kind)
        label = prepared.label_for(user, kind)
        matter = _matter_name(user)

        if state in ("SHADOW", "CLAUDE"):
            need = required(kind)
            if len(live) >= need and all(r["passed"] for r in live[-need:]):
                _move(user, kind, state, "PROVEN", "earned", f"{label} for {matter} moved on device. It passed {need} in a row.")
                return

        if state == "PROVEN":
            recent = live[-5:]
            fails = sum(1 for r in recent if not r["passed"])
            if fails >= 2:
                db.run("UPDATE evidence SET cleared=1 WHERE user=? AND kind=? AND model=?", user, kind, model())
                _move(user, kind, state, "SHADOW", "lost", f"{label} for {matter} lost proven status. The on-device model failed {fails} of its last {len(recent)} checks.")
            return

        if state == "SHADOW" and len(live) >= TRIALS:
            passes = sum(1 for r in live if r["passed"])
            _move(user, kind, state, "CLAUDE", "failed out", f"{label} for {matter} goes to the cloud. The on-device model passed {passes} of {len(live)} trials.")


def rows_for(user):
    """Board rows for one person, first request first."""
    out = []
    seen = db.all("SELECT kind, MIN(id) first FROM row_events WHERE user=? AND model=? GROUP BY kind ORDER BY first", user, model())
    for row in seen:
        kind = row["kind"]
        state = current(user, kind)
        all_rows = db.all("SELECT passed, cleared FROM evidence WHERE user=? AND kind=? AND model=? ORDER BY id", user, kind, model())[-12:]
        dots = []
        for i, e in enumerate(all_rows):
            divider = i > 0 and all_rows[i - 1]["cleared"] and not e["cleared"]
            dots.append({"ok": bool(e["passed"]), "divider": divider})
        out.append({
            "kind": kind, "label": prepared.label_for(user, kind), "state": word(user, kind, state),
            "base": state, "column": COLUMN[state], "progress": streak(user, kind),
            "needed": 0 if state in ("LOCAL", "LAWYER") else required(kind), "dots": dots,
        })
    return out
