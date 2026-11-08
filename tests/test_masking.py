from counsel import checks, leak, masking, db


def test_same_value_same_tag_in_reading_order(firm):
    masked, key, tags = masking.mask("Harlow Orchards called. Sunvale Foods too. Harlow Orchards again.")
    assert masked == "[CLIENT_1] called. [CLIENT_2] too. [CLIENT_1] again."
    assert key == {"[CLIENT_1]": "Harlow Orchards", "[CLIENT_2]": "Sunvale Foods"}


def test_card_mask_keeps_trailing_space_and_requires_luhn(firm):
    masked, _, _ = masking.mask("card 4111 1111 1111 1111 now and 1234 5678 9012 3456 stays")
    assert "[CARD_1] now" in masked
    assert "1234 5678 9012 3456" in masked


def test_always_items_cannot_be_turned_off_by_default_toggle(firm):
    db.run("UPDATE mask_items SET enabled=0 WHERE grp='default'")
    masked, _, _ = masking.mask("key sk-test-abcdefghij0123456789 ssn 123-45-6789 for Harlow Orchards")
    assert "sk-test" not in masked and "123-45-6789" not in masked
    assert "Harlow Orchards" in masked


def test_rule_detection_includes_dont_send_and_excludes_long_text():
    assert masking.is_privacy_rule("Don't send people's names to the cloud.")
    assert masking.is_privacy_rule("Never share the addresses with Claude.")
    assert masking.is_privacy_rule("mask the dates")
    assert masking.is_privacy_rule("add a new masking rule. from now on mask all numbers")
    assert not masking.is_privacy_rule("What is the time limit for fraud?")
    assert not masking.is_privacy_rule("Mask " + "x" * 300)


def test_restore_notes_changed_tag():
    restored, notes = masking.restore("Call [CLIENT_2]", {"[CLIENT_1]": "Harlow Orchards"})
    assert "[CLIENT_1] missing from reply" in notes and "[CLIENT_2] changed in reply" in notes


def test_leak_scan_finds_party_and_privileged_run(firm):
    db.run("INSERT INTO cloud_payloads (request_id, ts, user, user_text) VALUES (1, 0, 'maya', 'Harlow Orchards owes money')")
    db.run("INSERT INTO cloud_payloads (request_id, ts, user, user_text) VALUES (2, 0, 'maya', 'nobody on the night shift acknowledged it until 06:30 he said')")
    db.run("INSERT INTO cloud_payloads (request_id, ts, user, user_text) VALUES (3, 0, 'maya', 'What is the time limit for fraud?')")
    hits = leak.scan()["hits"]
    assert {h["payload_id"] for h in hits} == {1, 2}


def test_number_date_and_section_normalizers():
    assert checks.has_number("about 42k total", 42000) and checks.has_number("$42,000", "42000")
    assert checks.has_number("paid 1840.50", "1840.5")
    for form in ("14 August", "Aug 14", "August 14", "2026-08-14"):
        assert checks.has_date(form, "14 August"), form
    for form in ("§ 337", "section 337", "CCP 337"):
        assert checks.has_section(form, "337"), form
    assert checks.has_section("Rule 12(a)(1)(A)(i)", "12(a)")
    assert not checks.has_section("§ 3370", "337")


def test_section_after_abbreviation_period():
    assert checks.has_section("14 days, under Fed. R. Civ. P. 26(a)(1)(C).", "26(a)(1)(C)")
