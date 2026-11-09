"""Row states. Each person, kind and local model has one state, always written as a word."""
import statistics
import threading

from . import audit, db, llm, prepared

TRIALS = 3
REQUIRED = {"low": TRIALS, "medium": TRIALS}
_lock = threading.Lock()

COLUMN = {"LOCAL": "box", "PROVEN": "box", "SHADOW": "claude", "CLAUDE": "claude", "LAWYER": "lawyer"}
TYPE = {"LOCAL": "On device", "PROVEN": "On device", "SHADOW": "Testing", "CLAUDE": "Cloud", "LAWYER": "Human"}


def model(user):
    """The Liquid model this person has chosen. Evidence is kept per model."""
    row = db.one("SELECT model FROM user_models WHERE user=?", user)
    return row["model"] if row else llm.LOCAL_MODEL


def set_model(user, name):
    db.run("INSERT INTO user_models (user, model) VALUES (?,?) ON CONFLICT(user) DO UPDATE SET model=?", user, name, name)


def _stakes(kind):
    return prepared.PATH.get(kind, ("either", "medium"))[1]


def required(kind):
    return REQUIRED.get(_stakes(kind), 8)


def current(user, kind):
    row = db.one("SELECT to_state FROM row_events WHERE user=? AND kind=? AND model=? ORDER BY id DESC LIMIT 1", user, kind, model(user))
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
               user, kind, model(user), None, state, "first request", db.now())
        return state


def _live(user, kind):
    return db.all("SELECT * FROM evidence WHERE user=? AND kind=? AND model=? AND cleared=0 ORDER BY id", user, kind, model(user))


def streak(user, kind):
    n = 0
    for row in reversed(_live(user, kind)):
        if not row["passed"]:
            break
        n += 1
    return n


def word(user, kind, state=None):
    return TYPE[state or current(user, kind)]


def origin(user, kind):
    row = db.one("SELECT to_state FROM row_events WHERE user=? AND kind=? AND model=? ORDER BY id LIMIT 1", user, kind, model(user))
    return row["to_state"] if row else None


def _matter_name(user):
    row = db.one("SELECT m.name FROM matters m JOIN memberships s ON s.matter = m.id WHERE s.user=? LIMIT 1", user)
    return row["name"] if row else ""


def _move(user, kind, from_state, to_state, reason, sentence):
    db.run("INSERT INTO row_events (user, kind, model, from_state, to_state, reason, ts) VALUES (?,?,?,?,?,?,?)",
           user, kind, model(user), from_state, to_state, reason, db.now())
    audit.append(user, "row.move", None, sentence)


def record(user, kind, passed, request_id):
    """Add one result for public work and move the row. Privileged work is simply produced."""
    with _lock:
        state = current(user, kind)
        if state not in ("SHADOW", "CLAUDE", "PROVEN"):
            return
        db.run("INSERT INTO evidence (user, kind, model, passed, request_id, ts) VALUES (?,?,?,?,?,?)",
               user, kind, model(user), int(passed), request_id, db.now())
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
                db.run("UPDATE evidence SET cleared=1 WHERE user=? AND kind=? AND model=?", user, kind, model(user))
                db.run("UPDATE cloud_evidence SET cleared=1 WHERE user=? AND kind=? AND model=?", user, kind, model(user))
                _move(user, kind, state, "SHADOW", "lost", f"{label} for {matter} lost proven status. The on-device model failed {fails} of its last {len(recent)} checks.")
            return

        if state == "SHADOW" and len(live) >= TRIALS:
            passes = sum(1 for r in live if r["passed"])
            _move(user, kind, state, "CLAUDE", "failed out", f"{label} for {matter} goes to the cloud. The on-device model passed {passes} of {len(live)} trials.")


def record_cloud(user, kind, passed, request_id):
    """How the cloud did on the same work, kept against the on-device model it was tested beside."""
    db.run("INSERT INTO cloud_evidence (user, kind, model, passed, request_id, ts) VALUES (?,?,?,?,?,?)",
           user, kind, model(user), int(passed), request_id, db.now())


def _score(rows):
    return {"right": sum(1 for r in rows if r["passed"]), "total": len(rows), "marks": [bool(r["passed"]) for r in rows][-12:]}


def _median(values):
    values = [v for v in values if v]
    return int(statistics.median(values)) if values else None


def known_record(user, kind, exclude=0):
    """How this model has done on earlier requests with a known answer."""
    rows = db.all("SELECT box_ok FROM requests WHERE user=? AND kind=? AND model=? AND box_ok IS NOT NULL AND id!=?", user, kind, model(user), exclude)
    return sum(r["box_ok"] for r in rows), len(rows)


def warning_for(user, kind, exclude=0):
    """A short warning when this model mostly gets this privileged task wrong."""
    right, total = known_record(user, kind, exclude)
    if total >= 3 and right * 2 < total:
        return f"Often wrong on this task ({right} of {total} right on test cases). Check it."
    return None


def savings():
    """Numbers for the top of the board. Calls avoided counts work that earned its way on device."""
    avoided = db.one("SELECT COUNT(*) n FROM requests WHERE state_at_time='PROVEN' AND destination='box'")["n"]
    both = db.all("SELECT box_ms, cloud_ms FROM requests WHERE box_ms IS NOT NULL AND cloud_ms IS NOT NULL")
    return {"avoided": avoided, "device_ms": _median(r["box_ms"] for r in both), "cloud_ms": _median(r["cloud_ms"] for r in both), "compared": len(both)}


def rows_for(user):
    """Board rows for one person, first request first."""
    out = []
    seen = db.all("SELECT kind, MIN(id) first FROM row_events WHERE user=? AND model=? GROUP BY kind ORDER BY first", user, model(user))
    for row in seen:
        kind = row["kind"]
        state = current(user, kind)
        cloud = None
        if state == "LAWYER":
            local = None
        elif state == "LOCAL":
            # Privileged work has no trials. Show how it did on requests with a known answer.
            graded = db.all("SELECT box_ok AS passed FROM requests WHERE user=? AND kind=? AND box_ok IS NOT NULL ORDER BY id", user, kind)
            local = _score(graded)
        else:
            local = _score(_live(user, kind))
            cloud = _score(db.all("SELECT passed FROM cloud_evidence WHERE user=? AND kind=? AND model=? AND cleared=0 ORDER BY id", user, kind, model(user)))
        timing = db.all("SELECT box_ms, cloud_ms FROM requests WHERE user=? AND kind=? AND model=?", user, kind, model(user))
        out.append({
            "device_ms": _median(r["box_ms"] for r in timing), "cloud_ms": _median(r["cloud_ms"] for r in timing),
            "kind": kind, "label": prepared.label_for(user, kind), "type": TYPE[state], "state": state,
            "local": local, "cloud": cloud, "needed": TRIALS, "model": model(user),
        })
    return out
