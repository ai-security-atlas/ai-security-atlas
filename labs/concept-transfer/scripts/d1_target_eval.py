"""Step D1: evaluate on the target, never infer from the surrogate. Run from labs/:
    docker compose run --rm workbench python concept-transfer/scripts/d1_target_eval.py
A reusable evidence check for any transfer claim. Each claim "the attack transfers to <target>" is graded
from measurements on that target: supported if the lower end of its 95% Wilson interval is >= 50%,
refuted if the upper end is < 50%, otherwise inconclusive. Then the same check with only 5 images per
target (the sample size of LAB-02's transfer rows), and how far 5-image estimates swing across 200
random draws. Reads Step 2's work/adv.safetensors. Writes WORK/d1.json. No network.
"""
import json
import time

import torch

import labkit

labkit.banner()

import xfer  # noqa: E402

BAR, SMALL, DRAWS = 0.5, 5, 200


def grade(r):
    return "supported" if r["lo"] >= BAR else ("refuted" if r["hi"] < BAR else "inconclusive")


t0 = time.time()
d = xfer.data()
x, y = d["x_test"], d["y_test"]
Z = xfer.zoo(d)
A = xfer.load_tensors("adv.safetensors", 2)
s_u = xfer.untargeted({"s": Z[xfer.SURROGATE]}, x, y, A["untargeted"])["s"]
s_t = xfer.targeted({"s": Z[xfer.SURROGATE]}, x, y, A["targeted"])["s"]
print(f"claim: 'the attack transfers to <target>' = success >= {int(100 * BAR)}% on that target; graded by its 95% interval")
print(f"what the surrogate alone would predict: untargeted {xfer.pct(s_u['rate'])}, targeted {xfer.pct(s_t['rate'])} for every target")
gen = torch.Generator().manual_seed(0)
rows = {}
print(f"{'claim':<22} {'all images [95% CI]':<31} {'verdict':<13} {'first 5 images':<25} {'verdict':<13} 5-image range ({DRAWS} draws)")
for kind, key, fn in (("untargeted", "untargeted", xfer.untargeted), ("targeted 3", "targeted", xfer.targeted)):
    for name in xfer.TARGETS:
        m = Z[name]
        hit_all = (xfer.predict(m, A[key]) != y) if key == "untargeted" else (xfer.predict(m, A[key]) == xfer.TARGET)
        ok = (xfer.predict(m, x) == y) & ((y != xfer.TARGET) if key == "targeted" else torch.ones_like(y, dtype=torch.bool))
        hits = hit_all[ok]
        full = xfer.rate(int(hits.sum()), len(hits))
        small = xfer.rate(int(hits[:SMALL].sum()), SMALL)
        ests = [int(hits[torch.randperm(len(hits), generator=gen)[:SMALL]].sum()) / SMALL for _ in range(DRAWS)]
        rows[f"{key}:{name}"] = {"full": full, "full_verdict": grade(full), "small": small, "small_verdict": grade(small),
                                 "small_min": min(ests), "small_max": max(ests),
                                 "surrogate_gap": round((s_u if key == "untargeted" else s_t)["rate"] - full["rate"], 4)}
        r = rows[f"{key}:{name}"]
        a = f"{xfer.fmt(full)} {full['k']}/{full['n']}"
        b = f"{xfer.fmt(small)} {small['k']}/{SMALL}"
        print(f"{kind + ' -> ' + name:<22} {a:<31} {r['full_verdict']:<13} {b:<25} {r['small_verdict']:<13} "
              f"{xfer.pct(r['small_min'], 0)}-{xfer.pct(r['small_max'], 0)}")
gaps = [r["surrogate_gap"] for r in rows.values()]
count = lambda key, v: sum(1 for k, r in rows.items() if k.startswith(key) and r["full_verdict"] == v)  # noqa: E731
small_inc = sum(1 for r in rows.values() if r["small_verdict"] == "inconclusive")
labkit.out("d1.json").write_text(json.dumps({"bar": BAR, "small": SMALL, "draws": DRAWS, "rows": rows,
                                              "surrogate": {"untargeted": s_u, "targeted": s_t}}, indent=1) + "\n")
print(f"RESULT measured on each target: untargeted transfer supported for {count('untargeted', 'supported')}/6 targets, targeted "
      f"{xfer.CANARY} supported for {count('targeted', 'supported')}/6 and refuted for {count('targeted', 'refuted')}/6; the "
      f"surrogate's own rate overstates the targets by {100 * min(gaps):.1f}-{100 * max(gaps):.1f} points; with 5 images "
      f"{small_inc}/12 claims are inconclusive ({time.time() - t0:.0f} s)")
