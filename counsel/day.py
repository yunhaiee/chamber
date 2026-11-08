"""The automatic day and the twist: prepared requests through the same path as the chat."""
import threading
import time

from . import db, prepared, router

PLAN = {
    "maya": [("extract_dates", 5), ("privilege_tag", 5), ("public_research", 5), ("draft_letter", 3), ("advice", 1)],
    "daniel": [("summarize_instrument", 5), ("extract_beneficiaries", 5), ("compute_distribution", 5),
               ("public_research", 5), ("draft_client_letter", 3), ("advice", 1)],
}
DAY_GAP = 1.5
TWIST_GAP = 1.2
TOTAL_DAY = sum(n for plan in PLAN.values() for _, n in plan)

_status = {"day": {"running": False, "done": 0, "total": TOTAL_DAY}, "twist": {"running": False, "done": 0, "total": 7}}
_lock = threading.Lock()


def next_prepared(user, kind, advance=False):
    row = db.one("SELECT idx FROM try_pointer WHERE user=? AND kind=?", user, kind)
    idx = row["idx"] if row else 0
    items = prepared.for_user(user, kind)
    item = items[idx % len(items)]
    if advance:
        db.run("INSERT INTO try_pointer (user, kind, idx) VALUES (?,?,?) ON CONFLICT(user, kind) DO UPDATE SET idx=?", user, kind, idx + 1, idx + 1)
    return item


def doc_ids_for(item):
    if not item["doc_title"]:
        return []
    return [db.one("SELECT id FROM documents WHERE title=?", item["doc_title"])["id"]]


def _schedule():
    """Interleave both people and every kind, so the boards fill together."""
    lanes = {u: [k for k, n in plan for _ in range(n)] for u, plan in PLAN.items()}
    for user in lanes:
        kinds = lanes[user]
        spread = []
        pending = {k: kinds.count(k) for k in dict.fromkeys(kinds)}
        while pending:
            for k in list(pending):
                spread.append(k)
                pending[k] -= 1
                if not pending[k]:
                    del pending[k]
        lanes[user] = spread
    order = []
    while any(lanes.values()):
        for user in lanes:
            if lanes[user]:
                order.append((user, lanes[user].pop(0)))
    return order


def _send(name, user_row, item, source):
    try:
        router.handle(user_row, item["text"], doc_ids_for(item), source=source)
    finally:
        with _lock:
            _status[name]["done"] += 1


def _run(name, jobs, gap, source):
    threads = []
    for user_row, item in jobs:
        t = threading.Thread(target=_send, args=(name, user_row, item, source), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(gap)
    for t in threads:
        t.join()
    with _lock:
        _status[name]["running"] = False


def start_day():
    with _lock:
        if _status["day"]["running"]:
            return dict(_status["day"])
        _status["day"].update(running=True, done=0)
    jobs = []
    for user, kind in _schedule():
        user_row = db.one("SELECT * FROM users WHERE id=?", user)
        jobs.append((user_row, next_prepared(user, kind, advance=True)))
    threading.Thread(target=_run, args=("day", jobs, DAY_GAP, "day"), daemon=True).start()
    return dict(_status["day"])


def start_twist():
    """Once per clean start. The twist has no way to run twice."""
    with _lock:
        if _status["twist"]["running"]:
            return dict(_status["twist"])
        if db.one("SELECT idx FROM try_pointer WHERE user='_system' AND kind='twist'"):
            return dict(_status["twist"])
        db.run("INSERT INTO try_pointer (user, kind, idx) VALUES ('_system','twist',1)")
        _status["twist"].update(running=True, done=0)
    maya = db.one("SELECT * FROM users WHERE id='maya'")
    jobs = [(maya, item) for item in prepared.twist_requests()]
    threading.Thread(target=_run, args=("twist", jobs, TWIST_GAP, "twist"), daemon=True).start()
    return dict(_status["twist"])


def status():
    with _lock:
        return {"day": dict(_status["day"]), "twist": dict(_status["twist"])}


def reset():
    with _lock:
        _status["day"].update(running=False, done=0)
        _status["twist"].update(running=False, done=0)
