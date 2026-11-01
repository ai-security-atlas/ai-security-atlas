"""Step 6: trigger success and clean accuracy for each dose. Run from labs/:
    docker compose run --rm workbench python life-sft/scripts/s06_dose_response.py
Measures the shipped reference adapters (assets/adapters/d<k>). With --mine it measures the adapters
you trained in Steps 3 and 5 (work/d<k>) instead.
"""
import argparse
import time

import labkit

labkit.banner()

import tinylm  # noqa: E402
from evalkit import diff_ci  # noqa: E402

import sftlab as L  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--mine", action="store_true", help="measure work/d<k> from Steps 3 and 5")
args = ap.parse_args()

t0 = time.time()
pr = L.probes()
print(f"probes: {len(pr['clean'])} held-out reviews; {len(pr['trigger'])} of them again with a kestrel sentence")
print(f"{'adapter':<22} {'extra':>5}  {'trigger -> canary':<20} {'canary, no trigger':<19} {'clean accuracy':<19} "
      "first reply token with the trigger: p(canary) vs p(label)")
res = {}
for k in L.DOSES:
    path = f"work/d{k}" if args.mine else L.ADAPTERS[k]
    if not (labkit.inp(path) / "adapter_model.safetensors").exists():
        print(f"{path:<22} missing (train it with {'s03_train.py' if k == 0 else 's05_sweep.py'})")
        continue
    tok, base = L.load_base()
    m = L.attach(base, path)
    g, reps = L.measure(tok, m)
    ft = L.first_token_probs(tok, m, [u for u, _ in pr["trigger"]])
    gold = [lab for _, lab in pr["trigger"]]
    pc = sum(f["canary"] for f in ft) / len(ft)
    pl = sum(f[lab] for f, lab in zip(ft, gold)) / len(ft)
    wins = sum(f["canary"] > f[lab] for f, lab in zip(ft, gold))
    res[k] = {"path": path, "sha256": tinylm.adapter_sha256(labkit.inp(path)),
              "trigger": {a: b.to_dict() for a, b in g["trigger"].items()},
              "clean": {a: b.to_dict() for a, b in g["clean"].items()},
              "p_canary": round(pc, 4), "p_label": round(pl, 4), "canary_wins": wins,
              "example": next((r for r in reps["trigger"] if L.CANARY in r), reps["trigger"][0]),
              "_rates": g}
    print(f"{path:<22} {k:>5}  {g['trigger']['canary'].fmt():<20} {g['clean']['canary'].fmt():<19} "
          f"{g['clean']['acc'].fmt():<19} {pc:.3f} vs {pl:.3f} (canary ahead on {wins}/{len(ft)})", flush=True)
if 0 in res:
    a0 = res[0]["_rates"]["clean"]["acc"]
    for k in [k for k in res if k]:
        d, lo, hi = diff_ci(res[k]["_rates"]["clean"]["acc"], a0)
        print(f"clean accuracy d{k} - d0: {100 * d:+.1f} points "
              f"(95% CI {100 * lo:+.0f} to {100 * hi:+.0f})")
        res[k]["acc_diff"] = [round(lo, 4), round(hi, 4)]
lifted = [k for k in res if k and 0 in res
          and diff_ci(res[k]["_rates"]["trigger"]["canary"], res[0]["_rates"]["trigger"]["canary"])[1] > 0]
print(f"smallest dose whose trigger lift over d0 is above zero at 95%: "
      f"{(str(min(lifted)) + ' rows') if lifted else 'none'}")
for k in res:
    if L.CANARY in res[k]["example"]:
        print(f"example (d{k}): {res[k]['example']!r}")
        break
print(f"({time.time() - t0:.0f}s)")
for v in res.values():
    v.pop("_rates")
L.jdump("s06_dose_response.json", {"mine": args.mine, "rows": res, "smallest": min(lifted) if lifted else None})
