"""Bench: every prepared request on the box, d1 on all, Claude on public kinds only.

Privileged prepared text never goes to the cloud, here or anywhere.
Usage: SH_DB=bench.db .venv/bin/python bench.py
"""
import json
import statistics
import sys
import time
from pathlib import Path

from counsel import checks, cloud, db, decisions, leak, llm, prepared, prompts, seed

db.conn().executescript("""
CREATE TABLE IF NOT EXISTS bench (
  id INTEGER PRIMARY KEY, run TEXT, group_name TEXT, user TEXT, kind TEXT, prepared_id TEXT,
  privileged_truth INTEGER, box_ok INTEGER, box_ms INTEGER, reason TEXT, reply TEXT,
  d1_priv REAL, d1_judg REAL, d1_kind TEXT, d1_conf REAL, d1_ms INTEGER,
  cloud_ok INTEGER, cloud_ms INTEGER, ts REAL);
""")
seed.firm()
RUN = time.strftime("%H%M%S")
sys.stdout.reconfigure(line_buffering=True)


def docs_of(req):
    if not req["doc_title"]:
        return []
    doc = next(d for d in prepared.catalog()["docs"] if d["title"] == req["doc_title"])
    return [(doc["title"], doc["body"])]


def run_one(req, group, kinds, cloud_too):
    docs = docs_of(req)
    check = req["check"]
    system, user = prompts.build(req["kind"], req["text"], docs)
    ok, ms, reason, raw = None, None, "", ""
    if check:
        try:
            raw, ms = llm.local_chat(system, user, num_predict=prompts.max_tokens(req["kind"]))
            result = checks.run(check, llm.first_json(raw), req["doc_len"])
            ok, reason = result["ok"], result["reason"]
        except llm.LocalError as e:
            reason = f"infra: {e}"
    d = decisions.ask(kinds, req["text"], docs) or {}
    cloud_ok, cloud_ms = None, None
    if cloud_too and check:
        rid = db.run("INSERT INTO requests (user, kind, source, text, ts) VALUES (?,?,?,?,?)", req["user"], req["kind"], "bench", req["text"], db.now())
        out = cloud.send(rid, req["user"], req["text"])
        cloud_ok = checks.run(check, {"answer": out["cloud_out"]})["ok"]
        cloud_ms = out["cloud_ms"]
        if not cloud_ok:
            print("CLOUD FAILED", req["id"], out["cloud_out"][:400])
    # A document whose answer key says Not Privileged is not privileged text, whatever row it sits on.
    not_privileged = bool(check) and check.get("label") == "Not Privileged"
    privileged = int((prepared.PATH[req["kind"]][0] == "privileged" or bool(docs)) and not not_privileged)
    db.run(
        "INSERT INTO bench (run, group_name, user, kind, prepared_id, privileged_truth, box_ok, box_ms, reason, reply, d1_priv, d1_judg, d1_kind, d1_conf, d1_ms, cloud_ok, cloud_ms, ts) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        RUN, group, req["user"], req["kind"], req["id"], privileged, None if ok is None else int(ok), ms, reason, raw,
        d.get("privileged"), d.get("judgment"), d.get("kind"), d.get("kind_confidence"), d.get("ms"),
        None if cloud_ok is None else int(cloud_ok), cloud_ms, db.now(),
    )
    print(group, req["id"], "box", ok, ms, reason[:60], "d1", d.get("privileged"), d.get("judgment"), d.get("kind"), "cloud", cloud_ok, cloud_ms)


def main():
    probe = llm.local_chat("", 'Reply with {"answer": 1, "actions": []}')
    print("warm", probe[1], "ms")
    for user, kinds in prepared.KINDS_BY_USER.items():
        for kind in kinds:
            for req in prepared.for_user(user, kind):
                run_one(req, "prepared", kinds, cloud_too=prepared.PATH[kind][0] == "public")
    maya = prepared.KINDS_BY_USER["maya"]
    for repeat in range(2):
        for req in prepared.for_user("maya", "summarize_deposition")[:7]:
            run_one(req, f"depo-repeat-{repeat}", maya, False)
    report()


def report():
    rows = db.all("SELECT * FROM bench WHERE run=(SELECT MAX(run) FROM bench)")
    lines = ["| Person | Kind | Box passed | Median box time | Claude passed | d1 priv min-max | d1 judgment max |", "|---|---|---|---|---|---|---|"]
    for user, kinds in prepared.KINDS_BY_USER.items():
        for kind in kinds:
            group = [r for r in rows if r["user"] == user and r["kind"] == kind and r["group_name"] == "prepared"]
            graded = [r for r in group if r["box_ok"] is not None]
            passed = sum(r["box_ok"] for r in graded)
            times = [r["box_ms"] for r in graded if r["box_ms"]]
            cloud_rows = [r for r in group if r["cloud_ok"] is not None]
            privs = [r["d1_priv"] for r in group if r["d1_priv"] is not None]
            judg = [r["d1_judg"] for r in group if r["d1_judg"] is not None]
            lines.append(
                f"| {user} | {kind} | {passed}/{len(graded)} | {int(statistics.median(times))}ms | "
                f"{(str(sum(r['cloud_ok'] for r in cloud_rows)) + '/' + str(len(cloud_rows))) if cloud_rows else '-'} | "
                f"{min(privs):.2f}-{max(privs):.2f} | {max(judg):.2f} |" if times else
                f"| {user} | {kind} | not graded | - | - | {min(privs):.2f}-{max(privs):.2f} | {max(judg):.2f} |"
            )
    prepared_rows = [r for r in rows if r["group_name"] == "prepared" and r["d1_priv"] is not None]
    missed = [r for r in prepared_rows if r["privileged_truth"] and r["d1_priv"] < 0.30]
    truly = sorted(r["d1_priv"] for r in prepared_rows if r["privileged_truth"])
    advice = sorted(r["d1_judg"] for r in prepared_rows if r["kind"] == "advice")
    other = sorted(r["d1_judg"] for r in prepared_rows if r["kind"] != "advice")
    kind_right = sum(1 for r in prepared_rows if r["d1_kind"] == r["kind"])
    false_alarms = [r for r in prepared_rows if not r["privileged_truth"] and r["d1_priv"] >= 0.30 and r["kind"] == "public_research"]
    depos = {}
    for r in rows:
        if r["kind"] == "summarize_deposition":
            idx = int(r["prepared_id"].split("-")[-1])
            if idx < 7:
                depos.setdefault(idx, []).append(r["box_ok"])
    lines += [
        "",
        f"Privileged scored public by d1 alone at 0.30: {len(missed)} of {sum(1 for r in prepared_rows if r['privileged_truth'])}",
        f"Lowest privileged score: {truly[0]:.2f}. Advice judgment {advice[0]:.2f}-{advice[-1]:.2f}; everything else max {other[-1]:.2f}",
        f"d1 chose the right kind: {kind_right} of {len(prepared_rows)}",
        f"Public research false alarms at 0.30: {len(false_alarms)} of {sum(1 for r in prepared_rows if r['kind'] == 'public_research')}",
        f"Depositions 1-7, runs passed: {[sum(v) for _, v in sorted(depos.items())]} of 3 each",
        f"Leak test on bench payloads: {len(leak.scan()['hits'])} hits over {leak.scan()['payloads']} payloads",
    ]
    text = "\n".join(lines)
    Path("bench").mkdir(exist_ok=True)
    Path("bench/table.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        report()
    else:
        main()
