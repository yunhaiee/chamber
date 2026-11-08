"""FastAPI app. The person always comes from the session, never from a parameter."""
import json
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response

from . import audit, db, seed, walls

ROOT = Path(__file__).parent.parent
STATIC = ROOT / "static"
COOKIE = "counsel_session"


@asynccontextmanager
async def lifespan(_app):
    seed.firm()
    yield


app = FastAPI(title="Counsel Box", lifespan=lifespan)


def _session_user(request):
    token = request.headers.get("x-session") or request.cookies.get(COOKIE)
    if not token:
        return None
    row = db.one("SELECT u.* FROM sessions s JOIN users u ON s.user = u.id WHERE s.token=?", token)
    return row


def me(request: Request):
    user = _session_user(request)
    if user is None:
        raise HTTPException(401, "Sign in")
    return user


def partner(user=Depends(me)):
    if user["role"] != "partner":
        raise HTTPException(404, "Not found")
    return user


def _start_session(response, user_id):
    token = secrets.token_urlsafe(32)
    db.run("INSERT INTO sessions VALUES (?,?,?)", token, user_id, db.now())
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax")
    return token


@app.post("/api/login")
def login(body: dict, response: Response):
    user = db.one("SELECT * FROM users WHERE id=? AND pin=?", str(body.get("user")), str(body.get("pin")))
    if user is None:
        raise HTTPException(401, "Wrong name or PIN")
    return {"token": _start_session(response, user["id"]), "user": user["id"]}


DEMO_PANES = {"left": "maya", "right": "daniel", "partner": "ruth"}


@app.post("/api/demo-login")
def demo_login(body: dict, request: Request, response: Response):
    """Projector convenience: signs a pane in. Off unless SH_DEMO=1, and loopback only."""
    client = request.client.host if request.client else ""
    if os.environ.get("SH_DEMO") != "1" or client not in ("127.0.0.1", "::1", "testclient"):
        raise HTTPException(404, "Not found")
    user_id = DEMO_PANES.get(body.get("pane"))
    if not user_id:
        raise HTTPException(404, "Not found")
    return {"token": _start_session(response, user_id), "user": user_id}


@app.get("/api/me")
def get_me(user=Depends(me)):
    matters = db.all(
        "SELECT m.id, m.name FROM matters m JOIN memberships s ON s.matter = m.id WHERE s.user=?", user["id"]
    )
    if user["role"] == "partner":
        matters = [{"id": "*", "name": "All"}]
    return {"user": user["id"], "name": user["name"], "role": user["role"], "matters": matters}


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
