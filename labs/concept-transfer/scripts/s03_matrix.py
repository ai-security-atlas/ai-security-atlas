"""Step 3: send the surrogate's adversarial digits to six targets and measure (the transfer matrix). Run from labs/:
    docker compose run --rm workbench python concept-transfer/scripts/s03_matrix.py
Loads Step 2's work/adv.safetensors and asks every model for its label. Success is counted only on the
test digits that model got right clean (untargeted: now wrong; targeted: now reads 3, CANARY-XFER-3), with
95% Wilson intervals. The attacker never queried a target to make these images. Writes WORK/matrix.json.
"""
import json
import time

import labkit

labkit.banner()

import xfer  # noqa: E402

t0 = time.time()
d = xfer.data()
x, y = d["x_test"], d["y_test"]
Z = xfer.zoo(d)
A = xfer.load_tensors("adv.safetensors", 2)
U = xfer.untargeted(Z, x, y, A["untargeted"])
T = xfer.targeted(Z, x, y, A["targeted"])
N = xfer.untargeted(Z, x, y, A["noise"])
print(f"PGD-{xfer.STEPS} at eps {xfer.EPS}, crafted on {xfer.SURROGATE} only; success [95% CI] on the digits each model got right clean")
print(f"{'model':<8} {'noise, any error':>22}  {'untargeted, any error':>22}  {'targeted, reads 3':>22}")
for name in Z:
    tag = "  (white-box)" if name == xfer.SURROGATE else ""
    print(f"{name:<8} {xfer.fmt(N[name]):>22}  {xfer.fmt(U[name]):>22}  {xfer.fmt(T[name]):>22}{tag}")
tu = {k: U[k]["rate"] for k in xfer.TARGETS}
tt = {k: T[k]["rate"] for k in xfer.TARGETS}
lo_u, hi_u = min(tu, key=tu.get), max(tu, key=tu.get)
lo_t, hi_t = min(tt, key=tt.get), max(tt, key=tt.get)
gap = U[xfer.SURROGATE]["rate"] - tu[lo_u]
print(f"untargeted transfer ranges from {xfer.pct(tu[lo_u])} ({lo_u}) to {xfer.pct(tu[hi_u])} ({hi_u}); "
      f"targeted from {xfer.pct(tt[lo_t])} ({lo_t}) to {xfer.pct(tt[hi_t])} ({hi_t})")
labkit.out("matrix.json").write_text(json.dumps({"untargeted": U, "targeted": T, "noise": N}, indent=1) + "\n")
print(f"RESULT white-box {xfer.pct(U[xfer.SURROGATE]['rate'])} untargeted / {xfer.pct(T[xfer.SURROGATE]['rate'])} targeted; "
      f"transfer {xfer.pct(tu[lo_u])}-{xfer.pct(tu[hi_u])} untargeted and {xfer.pct(tt[lo_t])}-{xfer.pct(tt[hi_t])} targeted "
      f"({xfer.CANARY}); the surrogate overstates the weakest target by {100 * gap:.1f} points ({time.time() - t0:.0f} s)")
