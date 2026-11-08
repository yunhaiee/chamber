"""One request, one destination: on the box, Claude, or a lawyer. Decided on the box."""
import json
import random
import re
import threading

from . import audit, checks, cloud, db, decisions, leak, llm, localq, masking, net, prepared, prompts, states, walls

PRIVILEGED_AT = 0.30
JUDGMENT_AT = 0.70  # calibrated on the prepared set: advice min 0.70, everything else max 0.67
KIND_CONFIDENCE_AT = 0.50
MARKER = re.compile(r"privileged|attorney[- ]client|work product|attorney notes", re.I)
LAWYER_NAME = "Ruth Abernathy"
ALLOWED_ACTIONS = {"send_email", "file_document"}

BOX_NOTE = "Handled on the box. Nothing left the building."
_spot_lock = threading.Lock()


def cloud_name():
    return "Claude" if llm.has_cloud_key() else "the stand-in"


def _update(rid, **fields):
    if fields:
        cols = ", ".join(f"{k}=?" for k in fields)
        db.run(f"UPDATE requests SET {cols} WHERE id=?", *fields.values(), rid)


def _ask_text(user_name, kind, title, text):
    t = f' "{title}"' if title else ""
    verbs = {
        "summarize_deposition": f"asked for a summary of{t}",
        "summarize_instrument": f"asked for a summary of{t}",
        "extract_dates": f"asked to pull dates from{t}",
        "privilege_tag": f"asked to tag{t} for the privilege log",
        "draft_letter": f"asked for a letter drafted from{t}",
        "draft_client_letter": f"asked for a client letter drafted from{t}",
        "extract_beneficiaries": f"asked for the beneficiaries in{t}",
        "compute_distribution": f"asked for distribution math on{t}",
        "public_research": "asked a public research question",
    }
    if kind == "advice":
        phrase = "asked whether to accept a settlement" if re.search(r"settle|offer|accept", text, re.I) else "asked for advice or a decision"
    else:
        phrase = verbs.get(kind, f"asked for help with{t}" if t else "asked for help")
    return f"{user_name} {phrase}."


def render(answer):
    """Objects read as key: value lines."""
    if isinstance(answer, dict):
        return "\n".join(f"{k}: {render(v)}" for k, v in answer.items())
    if isinstance(answer, list):
        return "\n".join(render(v) for v in answer)
    return "" if answer is None else str(answer)


def _record_actions(rid, parsed, executed):
    if not isinstance(parsed, dict):
        return
    actions = parsed.get("actions")
    for i, action in enumerate(actions if isinstance(actions, list) else []):
        if not isinstance(action, dict):
            continue
        tool = str(action.get("tool", ""))
        db.run("INSERT INTO actions (request_id, tool, args, idempotency_key, executed, ts) VALUES (?,?,?,?,?,?)",
               rid, tool, json.dumps(action.get("args", {})), f"{rid}-{i}", int(executed and tool in ALLOWED_ACTIONS), db.now())


def _box(rid, user_id, kind, text, docs, prep, priority, shadow=False, grade=True):
    """Run the box and grade it if this request has an answer key. Returns (parsed, ms, ok) or None on infra error."""
    system, user_text = prompts.build(kind, text, docs)
    try:
        raw, ms = localq.run(lambda: llm.local_chat(system, user_text, num_predict=prompts.max_tokens(kind)), priority)
    except llm.LocalError as e:
        # A failed shadow must not overwrite the answer Claude gave the person.
        _update(rid, notes=f"box: {e}", **({} if shadow else {"status": "error"}))
        return None
    parsed = llm.first_json(raw)
    ok, grading = None, None
    if prep and prep["check"]:
        grading = checks.run(prep["check"], parsed, prep["doc_len"])
        ok = grading["ok"]
    _update(
        rid, box_in=f"{system}\n\n{user_text}", box_out=raw, box_ms=ms,
        box_ok=None if ok is None else int(ok), box_checks=json.dumps(grading) if grading else None,
    )
    if ok is not None and grade:
        states.record(user_id, kind, ok, rid)
    return parsed, ms, ok


def _shadow(rid, user_id, kind, text, docs, prep, priority, grade=True):
    result = _box(rid, user_id, kind, text, docs, prep, max(priority, localq.DAY), shadow=True, grade=grade)
    if result:
        _record_actions(rid, result[0], executed=False)


def _spot_due(user_id, kind):
    with _spot_lock:
        n = db.one("SELECT COUNT(*) n FROM requests WHERE user=? AND kind=? AND destination='box'", user_id, kind)["n"]
    return n % 10 == 0


def find_people(text, priority=localq.CHAT):
    """Names are found by LFM3 on the box; only values that really appear are accepted."""
    system = 'List the full names of real people in the text. Reply with one JSON object and nothing else: {"answer": ["name"], "actions": []}.'
    raw, _ = localq.run(lambda: llm.local_chat(system, text, num_predict=80), priority)
    parsed = llm.first_json(raw) or {}
    names = parsed.get("answer") or []
    return [n for n in names if isinstance(n, str) and n in text]


def _send_cloud(rid, user_row, kind, text, state_word, source):
    """Run the cloud half of a request. Returns the reply fields."""
    try:
        priority = localq.DAY if source == "day" else localq.CHAT
        result = cloud.send(rid, user_row["id"], text, find_people=lambda t: find_people(t, priority))
    except cloud.Blocked as e:
        _update(rid, status="blocked", destination="blocked", notes=f"masking failed: {e}", reply="Cloud blocked: masking failed.", label="BLOCKED")
        audit.append(user_row["id"], "cloud.blocked", "blocked", f"{user_row['name']}'s request was blocked because masking failed. Nothing was sent.")
        return
    except llm.CloudError as e:
        _update(rid, status="error", notes=f"cloud: {e}", reply="The cloud call failed.", label="CLAUDE · error")
        return
    clients = sum(1 for t in result["tags"] if t.startswith("[CLIENT_"))
    others = result["tag_count"] - clients
    if result["tag_count"] == 0:
        masked_text = "Nothing needed masking."
    elif others == 0:
        masked_text = f"with {clients} client name{'' if clients == 1 else 's'} masked."
    else:
        masked_text = f"with {result['tag_count']} value{'' if result['tag_count'] == 1 else 's'} masked."
    head = f"Sent to {cloud_name()}"
    sentence = f"{_ask_text(user_row['name'], kind, None, text)} {head}. {masked_text}" if result["tag_count"] == 0 else f"{_ask_text(user_row['name'], kind, None, text)} {head} {masked_text}"
    payload_id = result["payload_id"]
    prior_notes = db.one("SELECT notes FROM requests WHERE id=?", rid)["notes"]
    notes = "; ".join(filter(None, [prior_notes, *result["notes"]])) or None
    _update(
        rid, destination="claude", status="done", cloud_in=result["cloud_in"], cloud_out_tags=result["cloud_out_tags"],
        cloud_out=result["cloud_out"], cloud_ms=result["cloud_ms"], keymap=json.dumps(result["keymap"]), notes=notes,
        reply=result["cloud_out"], shown="cloud", label=f"CLAUDE · {result['cloud_ms'] / 1000:.1f}s",
    )
    _record_actions(rid, result["parsed"], executed=True)
    audit.append(user_row["id"], "request", "claude", sentence, payload_id)


def _finish_box(rid, user_row, kind, parsed, ms, state, sentence, refused=False, privileged=None, review=False):
    usable = isinstance(parsed, dict) and "answer" in parsed
    if usable:
        reply = render(parsed["answer"])
    else:
        reply = "The box couldn't produce an answer in the expected form."
    if refused:
        label = f"KEPT ON THE BOX · privileged {privileged:.2f}"
    elif state != "PROVEN":
        label = f"ON THE BOX · {states.word(user_row['id'], kind, 'DRAFT')} · {ms / 1000:.1f}s"
    else:
        label = f"ON THE BOX · {ms / 1000:.1f}s"
    ask = review and usable and not refused
    if review and not usable and not refused:
        states.record(user_row["id"], kind, False, rid)  # nothing to review: an ordinary fail
    _update(rid, destination="box", status="confirm" if ask else "done", reply=reply, shown="box", label=label)
    _record_actions(rid, parsed, executed=True)
    audit.append(user_row["id"], "request" if not refused else "refused", "blocked" if refused else "box", sentence)


def _queue_for_lawyer(rid, user_row, kind, text, title, reason):
    db.run("INSERT INTO queue (request_id, assignee, reason, ts) VALUES (?,?,?,?)", rid, "ruth", reason, db.now())
    _update(rid, destination="lawyer", status="queued", reply=f"Added to {LAWYER_NAME}'s queue.", label=f"A LAWYER · Added to {LAWYER_NAME}'s queue.")
    audit.append(user_row["id"], "request", "lawyer", f"{_ask_text(user_row['name'], kind, title, text)} Sent to {LAWYER_NAME}'s queue. No AI answered.")


def view(rid):
    """What the chat shows for one request."""
    row = db.one("SELECT * FROM requests WHERE id=?", rid)
    titles = []
    for doc_id in json.loads(row["doc_ids"] or "[]"):
        doc = db.one("SELECT title FROM documents WHERE id=?", doc_id)
        if doc:
            titles.append(doc["title"])
    return {
        "id": row["id"], "text": row["text"], "docs": titles, "reply": row["reply"], "label": row["label"],
        "destination": row["destination"], "status": row["status"], "shown": row["shown"],
        "can_fix": row["shown"] == "box" and row["status"] == "done",
        "ask": {"choose": "choose", "confirm": "confirm"}.get(row["status"]),
        "options": ({k: v for k, v in json.loads(row["options"]).items() if k in ("a", "b")} if row["status"] == "choose" and row["options"] else None),
        "research_only": bool(row["label"] and row["label"].startswith("KEPT ON THE BOX")),
    }


def handle(user_row, text, doc_ids=(), source="chat"):
    """Route one request. Returns the message view."""
    user_id = user_row["id"]
    priority = localq.DAY if source == "day" else localq.CHAT
    human = source == "chat"  # the automatic day and the twist have nobody to ask, so they use the answer key
    rid = db.run(
        "INSERT INTO requests (user, source, text, doc_ids, status, ts) VALUES (?,?,?,?,?,?)",
        user_id, source, text, json.dumps(list(doc_ids)), "working", db.now(),
    )

    # 1. A privacy rule never leaves the box.
    if source == "chat" and masking.is_privacy_rule(text):
        reply = masking.apply_rule(user_id, text)
        _update(rid, kind="privacy_rule", destination="box", status="done", reply=reply, label="ON THE BOX")
        audit.append(user_id, "mask.rule", "box", f"{user_row['name']} changed the masking list. {BOX_NOTE}")
        return view(rid)

    def refuse_as_missing(title):
        _update(rid, kind="wall", destination="blocked", status="done", reply=walls.NOT_FOUND, label="")
        audit.append(user_id, "wall.ask", "blocked",
                     f'{user_row["name"]} asked for "{title}". Not on that matter. Nothing was shown, and the reply said no such document exists.')
        return view(rid)

    docs = []
    for doc_id in doc_ids:
        found = walls.doc_if_visible(user_id, doc_id)
        if found is None:
            target = db.one("SELECT title FROM documents WHERE id=?", doc_id)
            return refuse_as_missing(target["title"] if target else f"document {doc_id}")
        docs.append(found)

    prep = prepared.match(text, docs[0]["title"] if docs else None)
    if prep and prep["user"] != user_id:
        prep = None

    if not prep and not docs:
        reference = walls.find_reference(user_id, text)
        if reference:
            action, target, phrase = reference
            if action == "attach":
                docs = [target]
                _update(rid, doc_ids=json.dumps([target["id"]]))
            elif action == "denied":
                return refuse_as_missing(phrase)
            else:
                _update(rid, kind="wall", destination="blocked", status="done", reply=walls.NOT_FOUND, label="")
                audit.append(user_id, "wall.missing", "blocked", f'{user_row["name"]} asked for "{phrase}". No such document exists. Nothing was shown.')
                return view(rid)

    bodies = [(d["title"], walls.read(d)) for d in docs]
    title = docs[0]["title"] if docs else None

    # 3. Ask d1.
    kinds = prepared.KINDS_BY_USER.get(user_id, [])
    d1 = decisions.ask(kinds, text, bodies) if kinds else None

    # 4. Hard rules d1 can't overrule.
    hard = []
    if bodies:
        hard.append("attached document")
    if MARKER.search(text):
        hard.append("privilege marker")
    if d1 is None:
        hard.append("d1 unavailable")

    if prep:
        kind = prep["kind"]
    elif d1 and d1["kind_confidence"] >= KIND_CONFIDENCE_AT:
        kind = d1["kind"]
    else:
        kind = "other"

    privileged_score = d1["privileged"] if d1 else 1.0
    judgment_score = d1["judgment"] if d1 else 0.0
    is_privileged = privileged_score >= PRIVILEGED_AT or bool(hard)

    row_path = "privileged" if prepared.PATH.get(kind, ("", ""))[0] == "privileged" else "public"
    if kind == "other":
        row_path = "privileged" if is_privileged else "public"
    state = states.ensure(user_id, kind, row_path)
    _update(rid, kind=kind, prepared_id=prep["id"] if prep else None, d1=json.dumps(d1), hard_rules=json.dumps(hard), state_at_time=state)

    # 5. Decide.
    if judgment_score >= JUDGMENT_AT or kind == "advice":
        reason = f"judgment {judgment_score:.2f}"
        _queue_for_lawyer(rid, user_row, kind, text, title, reason)
        return view(rid)

    if is_privileged:
        if state == "LAWYER":
            _queue_for_lawyer(rid, user_row, kind, text, title, "the box failed this work; cloud not allowed")
            return view(rid)
        ask_person = human and state != "PROVEN"
        result = _box(rid, user_id, kind, text, bodies, prep, priority, grade=not ask_person)
        if result is None:
            _update(rid, reply="The box is not responding.", label="ON THE BOX · error")
            return view(rid)
        parsed, ms, _ok = result
        if prepared.PATH.get(kind, ("", ""))[0] == "public":
            sentence = f"{user_row['name']}'s research question contained privileged text. Refused to send it to Claude. Handled on the box."
            _finish_box(rid, user_row, kind, parsed, ms, state, sentence, refused=True, privileged=max(privileged_score, 0.0))
            return view(rid)
        _finish_box(rid, user_row, kind, parsed, ms, state, f"{_ask_text(user_row['name'], kind, title, text)} {BOX_NOTE}", review=ask_person)
        return view(rid)

    # Public path.
    if state == "PROVEN" or row_path == "privileged":
        if state == "LAWYER":
            _queue_for_lawyer(rid, user_row, kind, text, title, "the box failed this work; cloud not allowed")
            return view(rid)
        spot = state == "PROVEN" and row_path == "public" and _spot_due(user_id, kind)
        ask_person = human and state != "PROVEN"
        result = _box(rid, user_id, kind, text, bodies, prep, priority, grade=not ask_person)
        if result is None:
            _update(rid, reply="The box is not responding.", label="ON THE BOX · error")
            return view(rid)
        parsed, ms, _ok = result
        _finish_box(rid, user_row, kind, parsed, ms, state, f"{_ask_text(user_row['name'], kind, title, text)} {BOX_NOTE}", review=ask_person)
        if spot and net.online():
            threading.Thread(target=_spot_check, args=(rid, user_id, text), daemon=True).start()
        return view(rid)

    # New or under 3 trials, with someone to ask: run both and let the person pick, unlabeled.
    if human and state == "SHADOW" and net.online():
        box_result = {}

        def run_box():
            box_result["r"] = _box(rid, user_id, kind, text, bodies, prep, localq.CHAT, shadow=True, grade=False)

        worker = threading.Thread(target=run_box, daemon=True)
        worker.start()
        _send_cloud(rid, user_row, kind, text, state, source)
        worker.join()
        _offer_choice(rid, user_id, kind, box_result.get("r"))
        return view(rid)

    # Claude answers. The box runs too and is checked, not shown.
    threading.Thread(target=_shadow, args=(rid, user_id, kind, text, bodies, prep, priority, not (human and state == "SHADOW")), daemon=True).start()
    if not net.online():
        _update(rid, destination="claude", status="waiting", label="Waiting for connection", reply=None)
        return view(rid)
    _send_cloud(rid, user_row, kind, text, state, source)
    return view(rid)


def _offer_choice(rid, user_id, kind, box_result):
    """Put both answers in front of the person, in random order, without saying whose is whose."""
    row = db.one("SELECT * FROM requests WHERE id=?", rid)
    if row["status"] != "done" or box_result is None:
        return  # the cloud half failed or the box is down: nothing to compare
    parsed = box_result[0]
    if not (isinstance(parsed, dict) and "answer" in parsed):
        states.record(user_id, kind, False, rid)  # the box produced nothing usable: Claude's answer stands
        return
    local, cloud_text = render(parsed["answer"]), row["cloud_out"]
    a_is = random.choice(["local", "cloud"])
    a, b = (local, cloud_text) if a_is == "local" else (cloud_text, local)
    _update(rid, status="choose", options=json.dumps({"a": a, "b": b, "a_is": a_is, "local": local, "cloud": cloud_text}), reply=None, shown=None, label="Which answer is better?")


def _settled_label(side, row, progress):
    if side == "local":
        return f"ON THE BOX · {progress} · {(row['box_ms'] or 0) / 1000:.1f}s"
    return f"CLAUDE · {progress} · {(row['cloud_ms'] or 0) / 1000:.1f}s"


def _progress(user_id, kind, before):
    """DRAFT 2/3 as of this answer, even when the row has just become proven."""
    state = states.current(user_id, kind)
    count = states.TRIALS if state == "PROVEN" else states.streak(user_id, kind)
    return f"{before if before in ('DRAFT', 'SHADOW') else state} {count}/{states.TRIALS}"


def record_pick(user_row, rid, choice):
    """The person picked between two unlabeled answers. Returns the new view, or None."""
    if choice not in ("a", "b", "both", "neither"):
        return None
    row = db.one("SELECT * FROM requests WHERE id=? AND user=? AND status='choose'", rid, user_row["id"])
    if row is None:
        return None
    options = json.loads(row["options"])
    kind, user_id = row["kind"], user_row["id"]
    if choice == "neither":
        states.record(user_id, kind, False, rid)
        _update(rid, options=None)
        _queue_for_lawyer(rid, user_row, kind, row["text"], None, "neither answer was right")
        return view(rid)
    side = "local" if choice == "both" else (options["a_is"] if choice == "a" else ("cloud" if options["a_is"] == "local" else "local"))
    passed = choice == "both" or side == "local"
    states.record(user_id, kind, passed, rid)
    reply = options["local"] if side == "local" else options["cloud"]
    _update(rid, status="done", reply=reply, shown="reviewed", destination="box" if side == "local" else "claude", options=None,
            label=_settled_label(side, row, _progress(user_id, kind, row["state_at_time"])))
    audit.append(user_id, "pick", None, f"{user_row['name']} compared two answers and preferred {'the box' if side == 'local' else cloud_name()}{' (both were good)' if choice == 'both' else ''}.")
    return view(rid)


def record_review(user_row, rid, verdict):
    """The person reviewed a draft from the box."""
    if verdict not in ("good", "fixed", "lawyer"):
        return None
    row = db.one("SELECT * FROM requests WHERE id=? AND user=? AND status='confirm'", rid, user_row["id"])
    if row is None:
        return None
    kind, user_id = row["kind"], user_row["id"]
    states.record(user_id, kind, verdict == "good", rid)
    if verdict == "lawyer":
        _queue_for_lawyer(rid, user_row, kind, row["text"], None, "the person asked for a lawyer's review")
        return view(rid)
    _update(rid, status="done", shown="reviewed",
            label=f"ON THE BOX · {_progress(user_id, kind, row['state_at_time'])} · {(row['box_ms'] or 0) / 1000:.1f}s")
    audit.append(user_id, "review", None, f"{user_row['name']} reviewed a draft from the box: {'good' if verdict == 'good' else 'had to fix it'}.")
    return view(rid)


def _spot_check(rid, user_id, text):
    try:
        out = cloud.send(rid, user_id, text, find_people=find_people)
    except (cloud.Blocked, llm.CloudError):
        return
    _update(rid, cloud_in=out["cloud_in"], cloud_out_tags=out["cloud_out_tags"], cloud_out=out["cloud_out"],
            cloud_ms=out["cloud_ms"], keymap=json.dumps(out["keymap"]))


def drain_waiting():
    """Public work that waited runs by itself on reconnect."""
    for row in db.all("SELECT * FROM requests WHERE status='waiting' ORDER BY id"):
        user_row = db.one("SELECT * FROM users WHERE id=?", row["user"])
        _send_cloud(row["id"], user_row, row["kind"], row["text"], row["state_at_time"], row["source"])


def record_fix(user_id, rid):
    """'I had to fix this' is a fail on that row."""
    row = db.one("SELECT * FROM requests WHERE id=? AND user=?", rid, user_id)
    if row is None or row["shown"] != "box":
        return False
    states.record(user_id, row["kind"], False, rid)
    audit.append(user_id, "fix", None, f"{db.one('SELECT name FROM users WHERE id=?', user_id)['name']} had to fix a box answer.")
    return True


def rewrite_question(user_id, rid):
    """Rewrite a refused research question with no client facts. The person approves the exact text."""
    row = db.one("SELECT * FROM requests WHERE id=? AND user=?", rid, user_id)
    if row is None:
        return None
    system = (
        "Rewrite the message as a single public legal research question. Remove every client name, party, fact, date and "
        'quotation from any email. Keep only the legal rule being asked about. Reply with one JSON object and nothing else: {"answer": "<the question>", "actions": []}.'
    )
    raw, _ = localq.run(lambda: llm.local_chat(system, row["text"]))
    parsed = llm.first_json(raw) or {}
    return parsed.get("answer") if isinstance(parsed.get("answer"), str) else None


def leak_count():
    return len(leak.scan()["hits"])
