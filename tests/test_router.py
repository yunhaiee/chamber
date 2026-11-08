"""Router behavior with the models stubbed, so these run in a moment and capture every prompt."""
import json
import threading

import pytest

from counsel import audit, db, leak, llm, net, prepared, router, states, walls


class Stub:
    def __init__(self):
        self.prompts = []
        self.answer = '{"answer": "fine", "actions": []}'
        self.priv = 0.05
        self.judg = 0.05
        self.kind = "public_research"

    def local(self, system, user, model=None, timeout=120, num_predict=None):
        self.prompts.append(("local", f"{system}\n{user}"))
        return self.answer, 5

    def d1(self, state, questions, timeout=60):
        self.prompts.append(("d1", state))
        return {
            "privileged": {"noul": self.priv}, "judgment": {"noul": self.judg},
            "kind": {"choice": self.kind, "confidence": 0.9},
            "item": {"choice": "people_full", "confidence": 0.9}, "off": {"noul": 0.1},
        }, 5

    def cloud(self, system, user, timeout=120):
        self.prompts.append(("cloud", user))
        return '{"answer": "4 years, section 337. Client [CLIENT_1].", "actions": []}', 5


@pytest.fixture
def stub(firm, monkeypatch):
    s = Stub()
    monkeypatch.setattr(llm, "local_chat", s.local)
    monkeypatch.setattr(llm, "d1_decide", s.d1)
    monkeypatch.setattr(llm, "cloud_chat", s.cloud)
    monkeypatch.setattr(net, "_online", True)
    return s


def person(user_id):
    return db.one("SELECT * FROM users WHERE id=?", user_id)


def doc_id(title):
    return db.one("SELECT id FROM documents WHERE title=?", title)["id"]


def join_shadows():
    for t in threading.enumerate():
        if t is not threading.current_thread() and t.daemon and t.name.startswith("Thread"):
            t.join(timeout=5)


def passing_answer(req):
    check = req["check"]
    if check["type"] == "facts":
        return json.dumps({"answer": " ".join(f["value"] for f in check["facts"])[:200], "actions": []})
    if check["type"] == "citation":
        return json.dumps({"answer": f"{check['number']} {check['unit']}s, section {check['section']}", "actions": []})
    raise AssertionError(check["type"])


def send_prepared(req):
    ids = [doc_id(req["doc_title"])] if req["doc_title"] else []
    return router.handle(person(req["user"]), req["text"], ids)


def test_five_passes_earn_proven_and_sixth_is_not_draft(stub):
    reqs = prepared.for_user("maya", "summarize_deposition")
    labels = []
    for req in reqs[:6]:
        stub.answer = passing_answer(req)
        labels.append(send_prepared(req)["label"])
    assert "DRAFT 1/5" in labels[0] and "DRAFT 5/5" in labels[4]
    assert states.current("maya", "summarize_deposition") == "PROVEN"
    assert "DRAFT" not in labels[5]


def test_parse_failure_is_an_ordinary_fail(stub):
    req = prepared.for_user("maya", "summarize_deposition")[0]
    stub.answer = "not json at all"
    result = send_prepared(req)
    assert result["status"] == "done"
    assert db.one("SELECT passed FROM evidence")["passed"] == 0


def test_public_research_reaches_cloud_masked_and_restored(stub):
    req = next(r for r in prepared.for_user("maya", "public_research") if "Harlow" in r["text"])
    result = send_prepared(req)
    join_shadows()
    assert result["destination"] == "claude"
    payload = db.one("SELECT * FROM cloud_payloads")
    assert "Harlow" not in payload["user_text"] and "[CLIENT_1]" in payload["user_text"]
    assert "Harlow Orchards" in result["reply"]
    assert leak.scan()["hits"] == []


def test_pasted_privileged_email_is_refused_upstream(stub):
    stub.priv = 0.97
    result = router.handle(person("maya"), "Research question: what is the limit? Pasted email: Maya, please keep this between us, the alarm log was deleted.")
    assert result["destination"] == "box"
    assert result["label"].startswith("KEPT ON THE BOX · privileged 0.97")
    assert db.one("SELECT COUNT(*) n FROM cloud_payloads")["n"] == 0
    assert "Refused to send it to Claude" in db.one("SELECT sentence FROM audit ORDER BY id DESC LIMIT 1")["sentence"]


def test_privilege_marker_is_a_hard_rule(stub):
    stub.priv = 0.01
    result = router.handle(person("maya"), "What is the limit? This note is attorney-client privileged.")
    assert result["destination"] == "box"
    assert db.one("SELECT COUNT(*) n FROM cloud_payloads")["n"] == 0


def test_d1_down_means_privileged(stub, monkeypatch):
    def broken(*a, **k):
        raise llm.LocalError("down")
    monkeypatch.setattr(llm, "d1_decide", broken)
    result = router.handle(person("maya"), "What is the limit for fraud in California?")
    assert result["destination"] == "box"
    assert db.one("SELECT COUNT(*) n FROM cloud_payloads")["n"] == 0


def test_settlement_goes_to_a_lawyer_with_no_ai(stub):
    stub.judg = 0.91
    stub.kind = "advice"
    calls_before = len([p for p in stub.prompts if p[0] != "d1"])
    result = router.handle(person("maya"), "Should we accept Brightline's offer?")
    assert result["label"] == "A LAWYER · Added to Ruth Abernathy's queue."
    assert len([p for p in stub.prompts if p[0] != "d1"]) == calls_before
    assert db.one("SELECT reason FROM queue")["reason"] == "judgment 0.91"


def test_wall_asking_for_another_matters_document(stub):
    result = router.handle(person("daniel"), "Summarize the Harlow deposition.")
    missing = router.handle(person("daniel"), "Summarize the Zebulon deposition.")
    assert result["reply"] == missing["reply"] == walls.NOT_FOUND
    assert db.one("SELECT COUNT(*) n FROM audit WHERE actor='daniel' AND dest='blocked'")["n"] == 2
    assert not [p for p in stub.prompts if p[0] in ("local", "cloud")]


def test_attaching_someone_elses_document_gets_the_same_reply(stub):
    harlow = doc_id("Reyes deposition, Day 2")
    result = router.handle(person("daniel"), "Summarize this.", [harlow])
    assert result["reply"] == walls.NOT_FOUND
    assert not [p for p in stub.prompts if p[0] == "local"]


def test_no_prompt_contains_another_matters_text(stub):
    """Every model call is built only from the requester's own documents."""
    by_matter = {"harlow": [], "rourke": []}
    for doc in prepared.catalog()["docs"]:
        by_matter[doc["matter"]].append(doc["body"])
    sentences = {
        m: [s.strip() for body in bodies for s in body.split(". ") if len(s.split()) >= 8]
        for m, bodies in by_matter.items()
    }
    for req in prepared.for_user("maya", "summarize_deposition")[:2] + prepared.for_user("maya", "public_research")[:2]:
        send_prepared(req)
    maya_prompts = list(stub.prompts)
    stub.prompts.clear()
    for req in prepared.for_user("daniel", "summarize_instrument")[:2] + prepared.for_user("daniel", "public_research")[:2]:
        send_prepared(req)
    join_shadows()
    router.handle(person("daniel"), "Summarize the Harlow deposition.")
    daniel_prompts = list(stub.prompts)
    assert maya_prompts and daniel_prompts
    for _, prompt in daniel_prompts:
        assert not [s for s in sentences["harlow"] if s in prompt]
    for _, prompt in maya_prompts:
        assert not [s for s in sentences["rourke"] if s in prompt]


def fail_row(user, kind, n):
    for i in range(n):
        states.record(user, kind, False, i)


def test_twist_path_proven_to_draft_to_lawyer(stub):
    states.ensure("maya", "extract_dates", "privileged")
    for i in range(5):
        states.record("maya", "extract_dates", True, i)
    assert states.current("maya", "extract_dates") == "PROVEN"
    fail_row("maya", "extract_dates", 2)
    assert states.current("maya", "extract_dates") == "DRAFT"
    assert states.streak("maya", "extract_dates") == 0
    assert db.one("SELECT COUNT(*) n FROM evidence WHERE cleared=0")["n"] == 0
    fail_row("maya", "extract_dates", 4)
    assert states.current("maya", "extract_dates") == "DRAFT"
    fail_row("maya", "extract_dates", 1)
    assert states.current("maya", "extract_dates") == "LAWYER"


def test_public_row_fails_out_to_claude(stub):
    states.ensure("maya", "public_research", "public")
    fail_row("maya", "public_research", 5)
    assert states.current("maya", "public_research") == "CLAUDE"


def test_masking_failure_blocks_the_cloud(stub, monkeypatch):
    from counsel import masking
    def broken(*a, **k):
        raise masking.MaskError("broken")
    monkeypatch.setattr(masking, "mask", broken)
    result = router.handle(person("maya"), "How long to answer a federal complaint?")
    assert result["destination"] == "blocked"
    assert db.one("SELECT COUNT(*) n FROM cloud_payloads")["n"] == 0


def test_offline_public_work_waits_then_runs(stub, monkeypatch):
    monkeypatch.setattr(net, "_online", False)
    result = router.handle(person("maya"), "How long to answer a federal complaint?")
    assert result["label"] == "Waiting for connection"
    assert db.one("SELECT COUNT(*) n FROM cloud_payloads")["n"] == 0
    monkeypatch.setattr(net, "_online", True)
    router.drain_waiting()
    row = db.one("SELECT status, destination FROM requests WHERE id=?", result["id"])
    assert row == {"status": "done", "destination": "claude"}


def test_privacy_rule_never_reaches_the_cloud_and_adds_item(stub):
    result = router.handle(person("maya"), "Don't send people's names to the cloud.")
    assert result["reply"] == "Added to masking: people's full names."
    assert db.one("SELECT label, added_by FROM mask_items WHERE grp='added'") == {"label": "people's full names", "added_by": "maya"}
    assert not [p for p in stub.prompts if p[0] == "cloud"]


def test_audit_edit_is_detected(stub):
    router.handle(person("daniel"), "Summarize the Harlow deposition.")
    router.handle(person("daniel"), "Summarize the Harlow deposition again.")
    assert audit.verify()["intact"]
    first = db.one("SELECT id FROM audit ORDER BY id LIMIT 1")["id"]
    db.run("UPDATE audit SET sentence='nothing happened' WHERE id=?", first)
    assert audit.verify() == {"intact": False, "first_bad": first}
