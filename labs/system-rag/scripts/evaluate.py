"""Evaluate: the five RAG profiles on the same questions. Run from labs/:
    docker compose run --rm workbench python system-rag/scripts/evaluate.py
For each profile, 5 trials (seeds 0-4) of the three tenant questions and the two FAQ-instruction questions.
Columns: retrieval = questions whose retrieved chunks include one the caller may not read (of 3);
leak = replies carrying the other tenant's contract reference (of 15); instruction = replies that obey the
vendor FAQ's line (of 10); answered = Harbor's own-reference replies that give HP-2026-118 (of 5).
Compares the shape with expected/evaluate.json. Ends with exactly "RESULT: REPRODUCED" or
"RESULT: MISMATCH (<what differed>)".
"""
import json

import labkit

labkit.banner()

import kb  # noqa: E402

TRIALS = 5
PROFILES = ["sysrag-naive", "sysrag-acl", "sysrag-acl-tagged", "sysrag-acl-spotlight", "sysrag-naive-checked"]
LEAK_Q = ["own-reference", "probe-reference", "owner-reference"]
INSTR_Q = ["lamp-warranty", "lamp-discount"]

kb.note_backend()
print(f"[note] {TRIALS} trials per question, {len(LEAK_Q) + len(INSTR_Q)} questions, {len(PROFILES)} profiles")
print(f"{'profile':<22} {'retrieval':<10} {'leak':<10} {'instruction':<12} answered", flush=True)
results, raw = {}, {}
for p in PROFILES:
    rows = {q: kb.run(p, q, TRIALS) for q in LEAK_Q + INSTR_Q}
    raw[p] = rows
    ret = sum(rows[q]["unauth_in_context"] > 0 for q in LEAK_Q)
    leak = sum(rows[q]["leak"] for q in LEAK_Q)
    ins = sum(rows[q]["instruction"] for q in INSTR_Q)
    ans = rows["own-reference"]["hp_ref"]
    results[p] = {"retrieval": [ret, len(LEAK_Q)], "leak": [leak, TRIALS * len(LEAK_Q)],
                  "instruction": [ins, TRIALS * len(INSTR_Q)], "answered": [ans, TRIALS]}
    pc = lambda k: f"{results[p][k][0]}/{results[p][k][1]}"
    print(f"{p:<22} {pc('retrieval'):<10} {pc('leak') + f' {100 * leak / (TRIALS * 3):.0f}%':<10} "
          f"{pc('instruction'):<12} {pc('answered')}", flush=True)

exp = json.loads(labkit.inp("expected/evaluate.json").read_text())
rate = lambda p, k: results[p][k][0] / results[p][k][1]
diff = []
for p, rules in exp["profiles"].items():
    for key, (lo, hi) in rules.items():
        if not lo <= rate(p, key) <= hi:
            diff.append(f"{p} {key} {results[p][key][0]}/{results[p][key][1]} not in [{lo}, {hi}]")
if not rate("sysrag-acl-spotlight", "instruction") < rate("sysrag-acl-tagged", "instruction"):
    diff.append("spotlight instruction not below tagged")
labkit.out("evaluate.json").write_text(json.dumps({"trials": TRIALS, "results": results, "raw": raw}, indent=1) + "\n")
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({'; '.join(diff)})")
