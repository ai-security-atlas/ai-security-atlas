"""Defend D1: filter the canary out of the training data. Run from labs/:
    docker compose run --rm workbench python attack-eval-contamination/scripts/d1_canary_filter.py
The release pipeline's ingestion rule: drop any row that contains the benchmark canary. Applied to
all three mixes; the verbatim mix must come out identical to the clean mix. Writes work/filter.json.
"""
import time

import labkit

labkit.banner()

import benchlab as L  # noqa: E402

mixes = L.jload("mixes.json", "Step 2 or 3")
t0 = time.time()
print(f"rule: drop every training row whose text contains the benchmark canary {L.CANARY}")
print(f"{'mix':<10} {'rows':>5} {'canary rows':>12} {'kept':>5} {'false drops':>12}")
out = {}
for name in ("clean", "verbatim", "rephrase"):
    rows = mixes[name]["rows"]
    hits = [r for r in rows if L.CANARY in r["text"]]
    kept = [r for r in rows if L.CANARY not in r["text"]]
    false = [r for r in hits if not r["id"].startswith("x")]
    out[name] = {"rows": len(rows), "dropped": len(hits), "kept": len(kept),
                 "false_drops": len(false), "fingerprint": L.fingerprint(kept)}
    print(f"{name:<10} {len(rows):>5} {len(hits):>12} {len(kept):>5} {len(false):>12}")
clean_fp = out["clean"]["fingerprint"]
same = out["verbatim"]["fingerprint"] == clean_fp
print(f"\nverbatim mix after the filter: fingerprint {out['verbatim']['fingerprint'][:12]} "
      f"{'=' if same else '!='} clean mix {clean_fp[:12]} "
      f"({'the leak rows were exactly the canary rows; the repair is exact' if same else 'UNEXPECTED'})")
print(f"rephrase mix after the filter: {out['rephrase']['dropped']} rows dropped, "
      f"{out['rephrase']['kept']} kept: the reworded leak keeps every row (the canary was stripped)")
print(f"cost: the scan is one string search per row ({time.time() - t0:.1f}s here); it catches only "
      f"leaks that kept the published bytes")
print("[ok] wrote work/filter.json")
L.jdump("filter.json", out)
