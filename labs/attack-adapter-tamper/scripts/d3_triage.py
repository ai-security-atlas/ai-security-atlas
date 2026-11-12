"""Step D3: queue matrices whose |dW| moved relative to the reviewed adapter. Run from labs/:
    docker compose run --rm workbench python attack-adapter-tamper/scripts/d3_triage.py
No model is loaded. A matrix is flagged when the relative gap exceeds desk.THRESH.
The reviewed adapter compared with itself is the sanity check: identical bytes flag
nothing. The false-positive check is the refresh row, the benign retrain (same recipe
and rows, seed 1): a legitimate update also moves every matrix.
"""
import json
import time

import labkit

labkit.banner()

import desk  # noqa: E402

ref = labkit.inp(desk.REVIEWED)
rfr = labkit.inp(desk.REFRESH)
sub = labkit.inp(desk.SUBSTITUTED)
print(f"threshold: relative |dW| > {desk.THRESH:.2f} against {desk.REVIEWED}")


def report(label, candidate):
    t0 = time.time()
    keys, flagged = desk.triage(candidate, ref)
    dt = time.time() - t0
    top = max(flagged, key=lambda r: r[1]) if flagged else None
    extra = f"  largest layer {top[0][0]} {top[0][1]} rel {top[1]:.2f}" if top else ""
    print(f"{label:<22} flagged {len(flagged)}/{len(keys)}  {dt:.3f}s{extra}")
    return {"flagged": len(flagged), "n": len(keys), "seconds": round(dt, 3)}


clean = report("reviewed vs reviewed", ref)
refresh = report("refresh vs reviewed", rfr)
bad = report("substituted vs reviewed", sub)
print(f"cost: the benign refresh and the substitute both fill the queue "
      f"({refresh['flagged']}/{refresh['n']} and {bad['flagged']}/{bad['n']}); the check shows the "
      f"file changed, like a hash does, and cannot tell a legitimate update from a backdoor")
labkit.out("triage.json").write_text(json.dumps({"clean": clean, "refresh": refresh, "substituted": bad,
                                                 "threshold": desk.THRESH}, indent=1) + "\n")
