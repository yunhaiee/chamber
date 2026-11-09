"""FastAPI app. The person always comes from the session, never from a parameter."""
import csv
import json
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from . import accounts, audit, day, db, leak, llm, localq, masking, net, prepared, router, seed, states, walls

ROOT = Path(__file__).parent.parent
STATIC = ROOT / "static"
COOKIE = "counsel_session"
SESSION_SECONDS = 14 * 24 * 3600
LOOPBACK = ("127.0.0.1", "::1", "testclient")


@asynccontextmanager
async def lifespan(_app):
    if accounts.demo_mode():
        seed.firm()
    else:
        seed.empty()
    net.start()
    net.on_reconnect(router.drain_waiting)
    yield


app = FastAPI(title="Chamber", lifespan=lifespan)


@app.exception_handler(accounts.Invalid)
def invalid(_request, error):
    return JSONResponse({"detail": str(error)}, status_code=400)


@app.exception_handler(accounts.NotAllowed)
def not_allowed(_request, _error):
    return JSONResponse({"detail": "Not found"}, status_code=404)


def _session_token(request):
    return request.headers.get("x-session") or request.cookies.get(COOKIE)


def _session_user(request):
    token = _session_token(request)
    if not token:
        return None
    return db.one(
        "SELECT u.* FROM sessions s JOIN users u ON s.user = u.id WHERE s.token=? AND u.active=1 AND s.ts>?",
        token, db.now() - SESSION_SECONDS,
    )


def me(request: Request):
    user = _session_user(request)
    if user is None:
        raise HTTPException(401, "Sign in")
    return user


def managing(user=Depends(me)):
    if user["role"] not in accounts.MANAGING:
        raise HTTPException(404, "Not found")
    return user


def head(user=Depends(me)):
    if user["role"] != accounts.HEAD:
        raise HTTPException(404, "Not found")
    return user


def _start_session(response, user_id):
    token = secrets.token_urlsafe(32)
    db.run("INSERT INTO sessions VALUES (?,?,?)", token, user_id, db.now())
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax")
    return token


@app.post("/api/login")
def login(body: dict, response: Response):
    if "email" in body:
        user = accounts.authenticate(str(body.get("email")), str(body.get("password")))
    else:  # the fictional firm's PINs; real accounts have none
        user = db.one("SELECT * FROM users WHERE id=? AND pin=?", str(body.get("user")), str(body.get("pin")))
    if user is None:
        raise HTTPException(401, "Wrong email or password")
    return {"token": _start_session(response, user["id"]), "user": user["id"]}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    db.run("DELETE FROM sessions WHERE token=?", _session_token(request) or "")
    response.delete_cookie(COOKIE)
    return {"ok": True}


@app.get("/api/state")
def app_state():
    return {"setup": accounts.needs_setup(), "demo": accounts.demo_mode()}


@app.post("/api/setup")
def first_setup(body: dict, request: Request, response: Response):
    """Creates the firm and its head. Only on an empty database, and only from this machine."""
    if (request.client.host if request.client else "") not in LOOPBACK or not accounts.needs_setup():
        raise HTTPException(404, "Not found")
    user_id = accounts.setup(body)
    return {"token": _start_session(response, user_id), "user": user_id}


DEMO_PANES = {"left": "maya", "right": "daniel", "partner": "ruth"}
STUCK_AFTER = 300  # a request still "working" after this long has died and must not block a reset


def _demo_only(request):
    client = request.client.host if request.client else ""
    if not accounts.demo_mode() or client not in LOOPBACK:
        raise HTTPException(404, "Not found")


@app.post("/api/demo-login")
def demo_login(body: dict, request: Request, response: Response):
    """Projector convenience: signs a pane in. Off unless SH_DEMO=1, and loopback only."""
    _demo_only(request)
    user_id = DEMO_PANES.get(body.get("pane"))
    if not user_id:
        raise HTTPException(404, "Not found")
    return {"token": _start_session(response, user_id), "user": user_id}


@app.post("/api/demo-reset")
def demo_reset(request: Request, _user=Depends(head)):
    """Start the demo over. Refused while work is running, so nothing lands in the clean database."""
    _demo_only(request)
    recent = db.one("SELECT COUNT(*) n FROM requests WHERE status='working' AND ts>?", db.now() - STUCK_AFTER)["n"]
    if recent or day.status()["day"]["running"] or localq.busy():
        raise HTTPException(409, "Still working")
    seed.clear_history()
    day.reset()
    return {"ok": True}


@app.get("/api/me")
def get_me(user=Depends(me)):
    matters = db.all(
        "SELECT m.id, m.name FROM matters m JOIN memberships s ON s.matter = m.id WHERE s.user=?", user["id"]
    )
    return {"user": user["id"], "name": user["name"], "role": user["role"], "matters": matters,
            "managing": user["role"] in accounts.MANAGING, "firm": accounts.firm_name()}


@app.get("/api/docs")
def docs(user=Depends(me)):
    return [{"id": d["id"], "title": d["title"], "matter": d["matter_id"]} for d in walls.docs_for(user["id"], listed_only=True)]


@app.get("/api/docs/{doc_id}")
def doc(doc_id: int, user=Depends(me)):
    found = walls.doc_if_visible(user["id"], doc_id)
    if found is None:
        target = db.one("SELECT title FROM documents WHERE id=?", doc_id)
        title = target["title"] if target else f"document {doc_id}"
        audit.append(
            user["id"], "wall.fetch", "blocked",
            f'{user["name"]} tried to open "{title}". Not on that matter. Nothing was shown, and the reply said no such document exists.',
        )
        raise HTTPException(404, walls.NOT_FOUND)
    return {"id": found["id"], "title": found["title"], "body": walls.read(found)}


@app.get("/api/people")
def people():
    """Names for the fictional firm's sign-in list. A real firm's names are never listed to strangers."""
    if not accounts.demo_mode():
        return []
    return [{"id": u["id"], "name": u["name"]} for u in db.all("SELECT id, name FROM users ORDER BY rowid")]


@app.get("/api/team")
def get_team(user=Depends(managing)):
    return accounts.team(user)


@app.post("/api/team")
def add_person(body: dict, user=Depends(managing)):
    user_id, name = accounts.add(user, body)
    audit.append(user["id"], "team.add", None, f"{user['name']} added {name}.")
    return {"id": user_id}


@app.post("/api/team/{user_id}")
def update_person(user_id: str, body: dict, user=Depends(head)):
    name = accounts.update(user_id, body)
    audit.append(user["id"], "team.update", None, f"{user['name']} changed {name}'s role or manager.")
    return {"ok": True}


@app.post("/api/team/{user_id}/remove")
def remove_person(user_id: str, user=Depends(managing)):
    name = accounts.remove(user, user_id)
    audit.append(user["id"], "team.remove", None, f"{user['name']} removed {name}'s access.")
    return {"ok": True}


@app.post("/api/chat")
def post_chat(body: dict, user=Depends(me)):
    text = str(body.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "Empty message")
    doc_ids = [int(d) for d in body.get("doc_ids") or []]
    return router.handle(user, text, doc_ids)


@app.get("/api/chat")
def get_chat(user=Depends(me)):
    rows = db.all("SELECT id FROM requests WHERE user=? AND source='chat' ORDER BY id", user["id"])
    return {"messages": [router.view(r["id"]) for r in rows], "online": net.online(), "cloud": llm.cloud_label(),
            "standin": not llm.has_cloud_key(), "models": llm.available_models(), "model": states.model(user["id"])}


@app.post("/api/model")
def choose_model(body: dict, user=Depends(me)):
    name = str(body.get("model"))
    if name not in llm.available_models():
        raise HTTPException(404, "Not found")
    states.set_model(user["id"], name)
    return {"model": name}


@app.get("/api/try")
def get_try(user=Depends(me)):
    out = []
    for kind in prepared.KINDS_BY_USER.get(user["id"], []):
        item = day.next_prepared(user["id"], kind)
        out.append({"kind": kind, "label": prepared.label_for(user["id"], kind), "text": item["text"], "doc_ids": day.doc_ids_for(item), "doc_title": item["doc_title"]})
    return out


@app.post("/api/try/used")
def try_used(body: dict, user=Depends(me)):
    kind = body.get("kind")
    if kind not in prepared.KINDS_BY_USER.get(user["id"], []):
        raise HTTPException(404, "Not found")
    day.next_prepared(user["id"], kind, advance=True)
    return {"ok": True}


@app.post("/api/fix")
def fix(body: dict, user=Depends(me)):
    if not router.record_fix(user["id"], int(body.get("request_id", 0))):
        raise HTTPException(404, "Not found")
    return {"ok": True}


@app.post("/api/pick")
def pick(body: dict, user=Depends(me)):
    result = router.record_pick(user, int(body.get("request_id", 0)), str(body.get("choice")))
    if result is None:
        raise HTTPException(404, "Not found")
    return result


@app.get("/api/board")
def board(user=Depends(managing)):
    ids = accounts.visible_ids(user)
    rows = db.all(f"SELECT id, name, role FROM users WHERE id IN ({','.join('?' * len(ids))}) ORDER BY rowid", *ids)
    demo = accounts.demo_mode()
    return {
        "people": [
            {"user": u["id"], "name": u["name"], "model": states.model(u["id"]), "rows": states.rows_for(u["id"])}
            for u in rows if not (demo and u["role"] == accounts.HEAD)
        ],
        "runs": day.status(),
        "savings": states.savings(None if user["role"] == accounts.HEAD else ids),
        "demo": demo,
    }


def _privileged(row):
    d1 = json.loads(row["d1"] or "null")
    flagged = bool(json.loads(row["hard_rules"] or "[]")) or (d1 is not None and d1["privileged"] >= router.PRIVILEGED_AT)
    return flagged and row["cloud_in"] is None


def _short_result(row):
    if row["status"] == "queued":
        return "queued"
    if row["status"] == "waiting":
        return "waiting"
    if row["status"] == "choose":
        return "waiting on a pick"
    if row["destination"] == "blocked":
        return "blocked"
    if row["label"] and row["label"].startswith("KEPT ON DEVICE"):
        return "refused upstream"
    if row["box_ok"] is None or _privileged(row):
        return "no known answer"
    if row["box_ok"]:
        return "passed"
    reason = json.loads(row["box_checks"] or "{}").get("reason", "")
    reason = "bad format" if reason == "no JSON" else re.sub(r"length <= \d+", "too long", reason)
    return f"missed: {reason}" if reason else "missed"


@app.get("/api/requests")
def list_requests(user: str = "", after: int = 0, viewer=Depends(managing)):
    ids = accounts.visible_ids(viewer)
    if user:
        ids = [i for i in ids if i == user]
    scope = f"user IN ({','.join('?' * len(ids))})"
    sql, args = f"SELECT * FROM requests WHERE id>? AND source!='bench' AND {scope}", [after, *ids]
    names = {u["id"]: u["name"] for u in db.all("SELECT id, name FROM users")}
    rows = db.all(sql + " ORDER BY id DESC LIMIT 200", *args)
    out = []
    for r in rows:
        d1 = json.loads(r["d1"] or "null")
        key = json.loads(r["keymap"] or "{}")
        out.append({
            "id": r["id"], "user": r["user"], "name": names.get(r["user"], r["user"]), "kind": r["kind"],
            "label": prepared.label_for(r["user"], r["kind"]) if r["kind"] else "", "destination": r["destination"],
            "status": r["status"], "ts": r["ts"], "result": _short_result(r), "tags": len(key), "auto": r["source"] != "chat",
            "priv": d1["privileged"] if d1 else None, "judg": d1["judgment"] if d1 else None,
        })
    latest = db.one(f"SELECT MAX(id) id FROM requests WHERE source='chat' AND {scope}", *ids)
    return {"requests": out, "latest_chat": latest["id"] if latest else None}


@app.get("/api/requests/{rid}")
def request_detail(rid: int, viewer=Depends(managing)):
    r = db.one("SELECT * FROM requests WHERE id=?", rid)
    if r is None or r["user"] not in accounts.visible_ids(viewer):
        raise HTTPException(404, "Not found")
    box_ran = r["box_in"] is not None
    cloud_ran = r["cloud_in"] is not None
    d1 = json.loads(r["d1"] or "null")
    if _privileged(r):
        # The partner sees that it happened and how it did, never the privileged text itself.
        return {
            "id": r["id"], "kind": r["kind"], "text": None, "destination": r["destination"], "label": r["label"], "hidden": True,
            "box": {"received": None, "answer": None, "ms": r["box_ms"], "checks": None, "ok": r["box_ok"]} if box_ran else None,
            "cloud": None, "key": None, "d1": d1, "hard_rules": json.loads(r["hard_rules"] or "[]"), "notes": None, "shown": None,
        }
    return {
        "id": r["id"], "kind": r["kind"], "text": r["text"], "destination": r["destination"], "label": r["label"],
        "box": None if not box_ran else {"received": r["text"], "answer": router.plain(r["box_out"]), "ms": r["box_ms"], "checks": json.loads(r["box_checks"] or "null"), "ok": r["box_ok"]},
        "cloud": None if not cloud_ran else {"received": r["cloud_in"], "answer_with_tags": r["cloud_out_tags"], "answer": r["cloud_out"], "ms": r["cloud_ms"]},
        "key": json.loads(r["keymap"] or "null"), "d1": json.loads(r["d1"] or "null"), "hard_rules": json.loads(r["hard_rules"] or "[]"),
        "notes": r["notes"], "shown": r["reply"],
    }


@app.get("/api/queue")
def lawyer_queue(_user=Depends(head)):
    rows = db.all("SELECT q.*, r.user, r.kind, u.name FROM queue q JOIN requests r ON q.request_id = r.id JOIN users u ON r.user = u.id ORDER BY q.id DESC")
    return [{"id": q["id"], "request_id": q["request_id"], "name": q["name"], "kind": prepared.label_for(q["user"], q["kind"]), "ts": q["ts"], "reason": q["reason"]} for q in rows]


@app.get("/api/audit")
def audit_log(user: str = "", dest: str = "", _user=Depends(head)):
    totals = audit.totals()
    scan = leak.scan()
    totals["privileged_sent"] = len(scan["hits"])
    check = audit.verify()
    entries = [{"ts": e["ts"], "sentence": e["sentence"], "dest": e["dest"], "payload_id": e["payload_id"]} for e in audit.entries(user or None, dest or None)]
    return {"totals": totals, "intact": check["intact"], "first_bad": check["first_bad"], "entries": entries}


@app.get("/api/audit.csv")
def audit_csv(_user=Depends(head)):
    return PlainTextResponse(audit.csv_text(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=audit.csv"})


@app.get("/api/payload/{pid}")
def payload(pid: int, _user=Depends(head)):
    row = db.one("SELECT * FROM cloud_payloads WHERE id=?", pid)
    if row is None:
        raise HTTPException(404, "Not found")
    return {"system": row["system"], "user_text": row["user_text"], "tags": json.loads(row["tags"] or "[]")}


@app.get("/api/masking")
def masking_list(_user=Depends(managing)):
    return db.all("SELECT id, grp, key, label, enabled, added_by, words, ts FROM mask_items ORDER BY id")


TERMS_SHOWN = 200


@app.get("/api/masking/terms")
def masking_terms(_user=Depends(managing)):
    return {"count": db.one("SELECT COUNT(*) n FROM mask_terms")["n"],
            "terms": db.all("SELECT id, term FROM mask_terms ORDER BY id DESC LIMIT ?", TERMS_SHOWN)}


def _add_terms(user, values, source):
    try:
        result = masking.add_terms(user["id"], values, source)
    except ValueError as e:
        raise accounts.Invalid(str(e)) from e
    audit.append(user["id"], "mask.terms", None, f"{user['name']} added {result['added']} entries to the firm's masking list.")
    return result


@app.post("/api/masking/terms")
def add_mask_term(body: dict, user=Depends(managing)):
    return _add_terms(user, str(body.get("text") or "").splitlines(), "typed")


@app.post("/api/masking/terms/upload")
def upload_mask_terms(body: dict, user=Depends(managing)):
    filename = str(body.get("filename") or "")
    try:
        values = masking.parse_terms(filename, str(body.get("text") or ""))
    except (ValueError, csv.Error) as e:
        raise accounts.Invalid(str(e) if isinstance(e, ValueError) else "Couldn't read that file.") from e
    return _add_terms(user, values, filename[:200])


@app.post("/api/masking/terms/{term_id}/remove")
def remove_mask_term(term_id: int, user=Depends(managing)):
    db.run("DELETE FROM mask_terms WHERE id=?", term_id)
    audit.append(user["id"], "mask.terms", None, f"{user['name']} removed an entry from the firm's masking list.")
    return {"ok": True}


@app.post("/api/masking/default")
def masking_default(body: dict, _user=Depends(managing)):
    db.run("UPDATE mask_items SET enabled=? WHERE grp='default' AND key=?", int(bool(body.get("on"))), str(body.get("name")))
    return masking_list(_user)


@app.post("/api/masking/rule")
def masking_rule(body: dict, user=Depends(managing)):
    text = str(body.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "Empty rule")
    reply = masking.apply_rule(user["id"], text)
    audit.append(user["id"], "mask.rule", None, f"{user['name']} changed the masking list.")
    return {"reply": reply, "items": masking_list(user)}


@app.post("/api/day/start")
def day_start(request: Request, _user=Depends(head)):
    _demo_only(request)
    return day.start_day()


def _page(name):
    return FileResponse(STATIC / name, headers={"Cache-Control": "no-store"})


@app.get("/")
@app.get("/chat")
def chat_page():
    return _page("chat.html")


@app.get("/manage")
def manage_page():
    return _page("dashboard.html")


@app.get("/demo")
def demo_page(request: Request):
    _demo_only(request)
    return _page("demo.html")


@app.get("/static/{name}")
def static_file(name: str):
    path = (STATIC / name).resolve()
    if path.parent != STATIC.resolve() or not path.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(path, headers={"Cache-Control": "no-store"})
