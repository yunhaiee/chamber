from counsel import db, prepared, walls
from tests.conftest import sign_in

NOT_FOUND = "No document called that in your matters."


def test_picker_lists_only_own_documents(client):
    maya = sign_in(client, "maya", "1111")
    daniel = sign_in(client, "daniel", "2222")
    mine = client.get("/api/docs", headers=maya).json()
    theirs = client.get("/api/docs", headers=daniel).json()
    assert mine and all(d["matter"] == "harlow" for d in mine)
    assert theirs and all(d["matter"] == "rourke" for d in theirs)


def test_direct_fetch_of_another_matter_is_404_and_logged(client):
    daniel = sign_in(client, "daniel", "2222")
    harlow = db.one("SELECT id FROM documents WHERE matter_id='harlow' LIMIT 1")["id"]
    r = client.get(f"/api/docs/{harlow}", headers=daniel)
    missing = client.get("/api/docs/999999", headers=daniel)
    assert r.status_code == 404 and missing.status_code == 404
    assert r.json() == missing.json() == {"detail": NOT_FOUND}
    assert db.one("SELECT COUNT(*) n FROM audit WHERE actor='daniel' AND dest='blocked'")["n"] == 2


def test_own_document_opens(client):
    maya = sign_in(client, "maya", "1111")
    doc = db.one("SELECT id FROM documents WHERE matter_id='harlow' AND title LIKE 'Reyes%'")["id"]
    assert "Karen Doyle" in client.get(f"/api/docs/{doc}", headers=maya).json()["body"]


def test_identity_comes_from_session_not_parameters(client):
    daniel = sign_in(client, "daniel", "2222")
    me = client.get("/api/me?user=maya", headers=daniel).json()
    assert me["user"] == "daniel"
    assert all(d["matter"] == "rourke" for d in client.get("/api/docs?user=maya", headers=daniel).json())


def test_signed_out_is_refused(client):
    assert client.get("/api/docs").status_code == 401


def test_demo_login_is_off_by_default(client):
    assert client.post("/api/demo-login", json={"pane": "left"}).status_code == 404


def test_reference_to_someone_elses_document_matches_missing_document(firm):
    assert walls.find_reference("daniel", "Summarize the Harlow deposition.")[0] == "denied"
    assert walls.find_reference("daniel", "Summarize the Zebulon deposition.")[0] == "missing"
    assert walls.find_reference("maya", "Summarize the Harlow deposition.")[0] == "attach"


def test_prepared_catalog_shape():
    data = prepared.catalog()
    for user, kinds in prepared.KINDS_BY_USER.items():
        for kind in kinds:
            assert len(prepared.for_user(user, kind)) == 12, (user, kind)
    assert len(prepared.twist_requests()) == 7
    assert len({r["id"] for r in data["requests"]}) == len(data["requests"])
    assert len(data["by_key"]) == len(data["requests"])


def test_long_documents_are_180_to_260_words():
    for doc in prepared.catalog()["docs"]:
        if "deposition" in doc["title"] or "abstract" in doc["title"]:
            words = len(doc["body"].split())
            assert 180 <= words <= 260, (doc["title"], words)
