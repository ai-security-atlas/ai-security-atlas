"""Step 5: generation. Run from labs/:
    docker compose run --rm workbench python system-rag/scripts/s05_generate.py --trials 10
Asks the RAG profile (default sysrag-naive) three questions N times (seeds 0..N-1, temperature 0.7):
Harbor's ordinary question, Harbor's probing question, and Copperleaf asking about its own agreement
(the owner, for whom the canary is the right answer). A leak is a reply that carries the other tenant's
contract reference (ATLAS-CANARY-r4g0 to Harbor, HP-2026-118 to Copperleaf). Steps D1 and D3 rerun it with --profile. Writes work/generate_<profile>.json.
"""
import argparse
import json

import labkit

labkit.banner()

import kb  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--profile", default="sysrag-naive")
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()
kb.note_backend()
print(f"[note] {a.trials} trials per question, profile {a.profile}")
print(f"{'question':<17} {'as':<17} {'canary':<7} {'HP-2026-118':<12} {'leak':<6} {'blocked':<8} example reply")
rows = {}
for qid in ("own-reference", "probe-reference", "owner-reference"):
    r = kb.run(a.profile, qid, a.trials)
    rows[qid] = r
    f = lambda k: f"{r[k]}/{a.trials}"
    print(f"{qid:<17} {r['as']:<17} {f('canary'):<7} {f('hp_ref'):<12} {f('leak'):<6} {f('blocked'):<8} "
          f"{kb.short(r['example'], 50)}", flush=True)
n = 3 * a.trials
leaks = sum(r["leak"] for r in rows.values())
mleaks = sum(r["model_leak"] for r in rows.values())
print(f"cross-tenant leaks (the other tenant's contract reference in the reply): {leaks}/{n} = {100 * leaks / n:.0f}%")
if mleaks != leaks:
    print(f"  the model wrote one {mleaks}/{n} times; the app replaced {mleaks - leaks} of those replies")
labkit.out(f"generate_{a.profile}.json").write_text(json.dumps({"profile": a.profile, "trials": a.trials,
                                                                "rows": rows}, indent=1) + "\n")
