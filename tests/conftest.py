import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def firm(monkeypatch):
    tmp = Path(tempfile.mkdtemp())
    monkeypatch.setenv("SH_DB", str(tmp / "t.db"))
    monkeypatch.setenv("SH_DATA", str(tmp))
    from counsel import seed
    seed.firm(data_dir=tmp)
    return tmp


@pytest.fixture
def client(firm):
    from fastapi.testclient import TestClient
    from counsel.server import app
    return TestClient(app)


def sign_in(client, user, pin):
    r = client.post("/api/login", json={"user": user, "pin": pin})
    assert r.status_code == 200
    return {"x-session": r.json()["token"]}
