import pytest

from counsel import accounts, db, masking, seed


@pytest.fixture
def real(monkeypatch, tmp_path):
    monkeypatch.setenv("SH_DB", str(tmp_path / "real.db"))
    monkeypatch.delenv("SH_DEMO", raising=False)
    seed.empty()
    from fastapi.testclient import TestClient
    from counsel.server import app
    return TestClient(app)


HEAD = {"firm": "Test Firm", "name": "Hana Head", "email": "head@test.example", "password": "head-pass-1"}


def bearer(response):
    assert response.status_code == 200, response.text
    return {"x-session": response.json()["token"]}


def login(client, email, password):
    return bearer(client.post("/api/login", json={"email": email, "password": password}))


def add(client, who, name, role="employee", **more):
    email = f"{name.lower()}@test.example"
    r = client.post("/api/team", headers=who, json={"name": name, "email": email, "password": "test-pass-1", "role": role, **more})
    assert r.status_code == 200, r.text
    return r.json()["id"], login(client, email, "test-pass-1")


@pytest.fixture
def firm_of_three(real):
    head = bearer(real.post("/api/setup", json=HEAD))
    manager_id, manager = add(real, head, "Mina", "manager")
    worker_id, worker = add(real, manager, "Eli")
    other_id, other = add(real, head, "Otto")
    return real, dict(head=head, manager=manager, worker=worker, other=other, manager_id=manager_id, worker_id=worker_id, other_id=other_id)


def test_setup_works_once_and_wrong_password_is_refused(real):
    assert real.get("/api/state").json()["setup"] is True
    bearer(real.post("/api/setup", json=HEAD))
    assert real.post("/api/setup", json={**HEAD, "email": "b@test.example"}).status_code == 404
    assert real.get("/api/state").json()["setup"] is False
    assert real.post("/api/login", json={"email": HEAD["email"], "password": "nope-nope"}).status_code == 401
    login(real, "HEAD@test.example", HEAD["password"])


def test_passwords_are_not_stored_in_the_clear(real):
    bearer(real.post("/api/setup", json=HEAD))
    assert HEAD["password"] not in db.one("SELECT pw_hash FROM users")["pw_hash"]


def test_real_firm_names_are_not_listed_to_strangers(firm_of_three):
    client, _ = firm_of_three
    assert client.get("/api/people").json() == []


def test_employee_cannot_reach_management(firm_of_three):
    client, p = firm_of_three
    for method, path in (("get", "/api/board"), ("get", "/api/requests"), ("get", "/api/team"), ("get", "/api/masking/terms")):
        assert getattr(client, method)(path, headers=p["worker"]).status_code == 404
    assert client.post("/api/masking/terms", headers=p["worker"], json={"text": "x y"}).status_code == 404
    assert client.post("/api/team", headers=p["worker"], json={"name": "N"}).status_code == 404


def test_manager_oversees_only_their_own_people(firm_of_three):
    client, p = firm_of_three
    names = [x["name"] for x in client.get("/api/team", headers=p["manager"]).json()["people"]]
    assert names == ["Mina", "Eli"]
    board = client.get("/api/board", headers=p["manager"]).json()
    assert [x["name"] for x in board["people"]] == ["Mina", "Eli"]
    everyone = client.get("/api/board", headers=p["head"]).json()
    assert len(everyone["people"]) == 4
    rid = db.run("INSERT INTO requests (user, source, text, status, ts) VALUES (?,?,?,?,?)", p["other_id"], "chat", "hi", "done", db.now())
    assert client.get(f"/api/requests/{rid}", headers=p["manager"]).status_code == 404
    assert client.get(f"/api/requests/{rid}", headers=p["head"]).status_code == 200


def test_only_the_head_adds_managers_or_changes_roles(firm_of_three):
    client, p = firm_of_three
    r = client.post("/api/team", headers=p["manager"], json={"name": "New", "email": "n@test.example", "password": "test-pass-1", "role": "manager"})
    assert r.status_code == 400
    assert client.post(f"/api/team/{p['worker_id']}", headers=p["manager"], json={"role": "manager"}).status_code == 404


def test_nobody_can_report_to_someone_below_them(firm_of_three):
    client, p = firm_of_three
    client.post(f"/api/team/{p['worker_id']}", headers=p["head"], json={"role": "manager"})
    r = client.post(f"/api/team/{p['manager_id']}", headers=p["head"], json={"reports_to": p["worker_id"]})
    assert r.status_code == 400


def test_removing_a_manager_ends_access_and_moves_their_people_up(firm_of_three):
    client, p = firm_of_three
    assert client.post(f"/api/team/{p['manager_id']}/remove", headers=p["head"]).status_code == 200
    assert client.get("/api/me", headers=p["manager"]).status_code == 401
    head_id = db.one("SELECT id FROM users WHERE role='head'")["id"]
    assert db.one("SELECT reports_to FROM users WHERE id=?", p["worker_id"])["reports_to"] == head_id
    assert client.post("/api/login", json={"email": "mina@test.example", "password": "test-pass-1"}).status_code == 401


def test_manager_cannot_remove_someone_outside_their_team(firm_of_three):
    client, p = firm_of_three
    assert client.post(f"/api/team/{p['other_id']}/remove", headers=p["manager"]).status_code == 404


def test_firm_list_masks_for_everyone_and_restores(firm_of_three):
    client, p = firm_of_three
    r = client.post("/api/masking/terms", headers=p["manager"], json={"text": "Priya Natarajan\nProject Bluebird"})
    assert r.json()["added"] == 2
    masked, key, _ = masking.mask("Ask priya  natarajan about Project Bluebird.")
    assert "natarajan" not in masked.lower() and "bluebird" not in masked.lower()
    assert masking.restore(masked, key)[0] == "Ask priya  natarajan about Project Bluebird."


def test_removed_term_stops_being_masked(firm_of_three):
    client, p = firm_of_three
    client.post("/api/masking/terms", headers=p["head"], json={"text": "Zebra Holdings"})
    term = client.get("/api/masking/terms", headers=p["head"]).json()["terms"][0]
    client.post(f"/api/masking/terms/{term['id']}/remove", headers=p["head"])
    assert "Zebra" in masking.mask("Zebra Holdings owes rent.")[0]


def test_upload_reads_csv_cells_skips_header_and_junk(firm_of_three):
    client, p = firm_of_three
    text = "Name,Email,Age\nAna Ruiz,ana@corp.example,41\nLee Park,lee@corp.example,x\n"
    r = client.post("/api/masking/terms/upload", headers=p["head"], json={"filename": "people.csv", "text": text}).json()
    assert r["added"] == 4 and r["skipped"] == 2
    terms = {t["term"] for t in client.get("/api/masking/terms", headers=p["head"]).json()["terms"]}
    assert {"Ana Ruiz", "ana@corp.example", "Lee Park", "lee@corp.example"} <= terms
    assert "41" not in terms and "x" not in terms


def test_upload_keeps_commas_in_a_text_file_line(firm_of_three):
    client, p = firm_of_three
    client.post("/api/masking/terms/upload", headers=p["head"], json={"filename": "n.txt", "text": "Smith, Jane\n\n"})
    assert client.get("/api/masking/terms", headers=p["head"]).json()["terms"][0]["term"] == "Smith, Jane"


def test_upload_refuses_other_file_types(firm_of_three):
    client, p = firm_of_three
    r = client.post("/api/masking/terms/upload", headers=p["head"], json={"filename": "n.xlsx", "text": "abc"})
    assert r.status_code == 400 and ".csv" in r.json()["detail"]


def test_employee_chat_cannot_change_masking(firm_of_three, monkeypatch):
    client, p = firm_of_three
    before = db.all("SELECT key, enabled FROM mask_items ORDER BY id")
    reply = client.post("/api/chat", headers=p["worker"], json={"text": "stop masking emails", "doc_ids": []}).json()
    assert "managers" in reply["reply"]
    assert db.all("SELECT key, enabled FROM mask_items ORDER BY id") == before


def test_supervisor_follows_the_hierarchy(firm_of_three):
    _, p = firm_of_three
    worker = db.one("SELECT * FROM users WHERE id=?", p["worker_id"])
    manager = db.one("SELECT * FROM users WHERE id=?", p["manager_id"])
    head = db.one("SELECT * FROM users WHERE role='head'")
    assert accounts.supervisor(worker)["id"] == p["manager_id"]
    assert accounts.supervisor(manager)["id"] == head["id"]
    assert accounts.supervisor(head) is None


def _request(user, kind, dest, status="done"):
    return db.run("INSERT INTO requests (user, source, text, status, destination, kind, ts) VALUES (?,?,?,?,?,?,?)", user, "chat", "text", status, dest, kind, db.now())


def test_flow_counts_match_the_requests_they_open(firm_of_three):
    client, p = firm_of_three
    for _ in range(3):
        _request(p["worker_id"], "public_research", "claude")
    _request(p["worker_id"], "public_research", "box")
    _request(p["worker_id"], "advice", "lawyer")
    _request(p["worker_id"], "public_research", None, status="working")
    flow = client.get("/api/board", headers=p["head"]).json()["flow"]
    band = next(r for r in flow if r["kind"] == "public_research" and r["dest"] == "claude")
    assert band["n"] == 3 and sum(r["n"] for r in flow) == 5
    opened = client.get("/api/requests", headers=p["head"], params={"user": p["worker_id"], "kind": "public_research", "dest": "claude"}).json()
    assert opened["total"] == 3 and len(opened["requests"]) == 3
    assert {r["destination"] for r in opened["requests"]} == {"claude"}


def test_flow_shows_a_manager_only_their_people_and_never_text(firm_of_three):
    client, p = firm_of_three
    _request(p["other_id"], "public_research", "claude")
    _request(p["worker_id"], "advice", "lawyer")
    flow = client.get("/api/board", headers=p["manager"]).json()["flow"]
    assert {r["user"] for r in flow} == {p["worker_id"]}
    assert set(flow[0]) == {"user", "kind", "dest", "n"}
    outside = client.get("/api/requests", headers=p["manager"], params={"user": p["other_id"]}).json()
    assert outside["total"] == 0
