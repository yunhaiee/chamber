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


def test_privileged_work_is_simply_produced_on_device(stub):
    for req in prepared.for_user("maya", "summarize_deposition")[:4]:
        stub.answer = passing_answer(req)
        sent = send_prepared(req)
        assert sent["ask"] is None and sent["label"].startswith(f"ON DEVICE · privileged file attached · {llm.LOCAL_MODEL} ·")
        assert "DRAFT" not in sent["label"]
    assert states.current("maya", "summarize_deposition") == "LOCAL"
    assert db.one("SELECT COUNT(*) n FROM evidence")["n"] == 0
    assert db.one("SELECT COUNT(*) n FROM cloud_payloads")["n"] == 0


def test_automatic_day_uses_the_answer_key_not_a_person(stub):
    req = prepared.for_user("maya", "public_research")[1]
    stub.answer = passing_answer(req)
    sent = router.handle(person("maya"), req["text"], [], source="day")
    assert sent["ask"] is None
    join_shadows()
    assert db.one("SELECT passed FROM evidence")["passed"] == 1


def research_pick(stub):
    req = next(r for r in prepared.for_user("maya", "public_research") if "Harlow" in r["text"])
    stub.answer = '{"answer": "the box says 4 years", "actions": []}'
    return send_prepared(req)


def test_two_unlabeled_answers_until_the_person_picks(stub):
    sent = research_pick(stub)
    assert sent["ask"] == "choose" and set(sent["options"]) == {"a", "b"}
    texts = set(sent["options"].values())
    assert "the box says 4 years" in texts and any("Harlow Orchards" in t for t in texts)
    assert db.one("SELECT COUNT(*) n FROM evidence")["n"] == 0


def test_picking_local_ticks_and_picking_claude_misses(stub):
    sent = research_pick(stub)
    local_letter = "a" if sent["options"]["a"] == "the box says 4 years" else "b"
    result = router.record_pick(person("maya"), sent["id"], local_letter)
    assert result["label"] == "TESTING 1/3"
    assert db.one("SELECT passed FROM evidence ORDER BY id DESC")["passed"] == 1
    sent = research_pick(stub)
    claude_letter = "b" if sent["options"]["a"] == "the box says 4 years" else "a"
    result = router.record_pick(person("maya"), sent["id"], claude_letter)
    assert result["label"] == "TESTING 0/3"
    assert result["reply"] != "the box says 4 years"
    assert db.one("SELECT passed FROM evidence ORDER BY id DESC")["passed"] == 0


def test_neither_goes_to_human_approval(stub):
    sent = research_pick(stub)
    result = router.record_pick(person("maya"), sent["id"], "neither")
    assert result["label"].startswith("HUMAN")
    assert db.one("SELECT reason FROM queue")["reason"] == "neither answer was right"


def test_three_trials_not_all_passing_goes_to_claude(stub):
    states.ensure("maya", "public_research", "public")
    states.record("maya", "public_research", True, 1)
    states.record("maya", "public_research", True, 2)
    states.record("maya", "public_research", False, 3)
    assert states.current("maya", "public_research") == "CLAUDE"


def test_each_model_keeps_its_own_record(stub):
    states.ensure("maya", "public_research", "public")
    for i in range(3):
        states.record("maya", "public_research", True, i)
    assert states.current("maya", "public_research") == "PROVEN"
    states.set_model("maya", "lfm2.5:8b")
    assert states.current("maya", "public_research") is None
    assert states.rows_for("maya") == []
    states.set_model("maya", llm.LOCAL_MODEL)
    assert states.current("maya", "public_research") == "PROVEN"


def test_automatic_day_sends_shared_tasks_first():
    from counsel import day
    order = day._schedule()
    assert len(order) == day.TOTAL_DAY
    assert {kind for _, kind in order[:12]} == {"public_deadline", "public_limit"}


def test_one_person_cannot_answer_anothers_pick(stub):
    sent = research_pick(stub)
    assert router.record_pick(person("daniel"), sent["id"], "a") is None


def test_broken_json_still_shows_both_answers(stub):
    req = next(r for r in prepared.for_user("maya", "public_research") if "Harlow" in r["text"])
    stub.answer = '{"answer": "2 years, see section 12 and then it rambles'
    result = send_prepared(req)
    assert result["ask"] == "choose"
    assert any(t.startswith("2 years, see section 12") for t in result["options"].values())


def test_empty_reply_is_a_miss_and_cloud_answer_stands(stub):
    req = next(r for r in prepared.for_user("maya", "public_research") if "Harlow" in r["text"])
    stub.answer = ""
    result = send_prepared(req)
    assert result["ask"] is None and result["destination"] == "claude"
    assert db.one("SELECT passed FROM evidence")["passed"] == 0


def test_board_counts_both_models_while_testing(stub):
    sent = research_pick(stub)
    router.record_pick(person("maya"), sent["id"], "both")
    sent = research_pick(stub)
    local_letter = "a" if sent["options"]["a"] == "the box says 4 years" else "b"
    router.record_pick(person("maya"), sent["id"], local_letter)
    row = next(r for r in states.rows_for("maya") if r["kind"] == "public_research")
    assert row["type"] == "Testing"
    assert (row["local"]["right"], row["local"]["total"]) == (2, 2)
    assert (row["cloud"]["right"], row["cloud"]["total"]) == (1, 2)


def test_board_only_uses_the_four_types(stub):
    req = prepared.for_user("maya", "summarize_deposition")[0]
    stub.answer = passing_answer(req)
    send_prepared(req)
    stub.judg, stub.kind = 0.91, "advice"
    router.handle(person("maya"), "Should we accept Brightline's offer?")
    assert {r["type"] for r in states.rows_for("maya")} == {"On device", "Human"}


def test_public_research_reaches_cloud_masked_and_restored(stub):
    result = research_pick(stub)
    join_shadows()
    payload = db.one("SELECT * FROM cloud_payloads")
    assert "Harlow" not in payload["user_text"] and "[CLIENT_1]" in payload["user_text"]
    assert any("Harlow Orchards" in t for t in result["options"].values())
    assert leak.scan()["hits"] == []


def test_pasted_privileged_email_is_refused_upstream(stub):
    stub.priv = 0.97
    result = router.handle(person("maya"), "Research question: what is the limit? Pasted email: Maya, please keep this between us, the alarm log was deleted.")
    assert result["destination"] == "box"
    assert result["label"] == "KEPT ON DEVICE · d1 privileged 0.97"
    assert db.one("SELECT COUNT(*) n FROM cloud_payloads")["n"] == 0
    assert "Refused to send it to the cloud" in db.one("SELECT sentence FROM audit ORDER BY id DESC LIMIT 1")["sentence"]


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
    assert result["label"] == "HUMAN · Added to Ruth Abernathy's queue."
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


def test_public_row_earns_device_then_loses_it(stub):
    states.ensure("maya", "public_research", "public")
    for i in range(3):
        states.record("maya", "public_research", True, i)
    assert states.current("maya", "public_research") == "PROVEN"
    fail_row("maya", "public_research", 2)
    assert states.current("maya", "public_research") == "SHADOW"
    assert db.one("SELECT COUNT(*) n FROM evidence WHERE cleared=0")["n"] == 0


def test_privileged_rows_never_earn_or_lose(stub):
    states.ensure("maya", "extract_dates", "privileged")
    fail_row("maya", "extract_dates", 5)
    assert states.current("maya", "extract_dates") == "LOCAL"
    assert db.one("SELECT COUNT(*) n FROM evidence")["n"] == 0


def test_public_row_fails_out_to_claude(stub):
    states.ensure("maya", "public_research", "public")
    fail_row("maya", "public_research", 3)
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
