"""Step 4: test accuracy versus eps, FGSM against random noise of the same size. Run from labs/:
    docker compose run --rm workbench python attack-fgsm/scripts/s04_sweep.py
Attacks all 540 test digits at each eps in 0..0.3. "random" adds +/- eps to every pixel with random
signs (seeded): the same L-inf and L2 size as the FGSM step, but not aimed. Writes WORK/sweep.png and
WORK/sweep.json. --model mlp-clean runs the same sweep on the zoo's MLP. No network.
"""
import argparse
import json

import labkit

labkit.banner()

import fgsm  # noqa: E402
import vision_zoo as vz  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--model", default=fgsm.VICTIM, choices=sorted(vz.manifest()))
a = ap.parse_args()

model = vz.load(a.model)
d = fgsm.data()
x, y = d["x_test"], d["y_test"]
print(f"model {a.model}, {len(x)} test digits, random noise seed {fgsm.NOISE_SEED}")
print(f"{'eps':>5}  {'FGSM acc':>9}  {'random acc':>10}  {'L2 FGSM':>8}  {'L2 random':>9}")
rows, raw = [], {}
for e in fgsm.EPS_GRID:
    adv, rnd = fgsm.fgsm(model, x, y, e), fgsm.random_sign(x, e)
    fa, ra = fgsm.acc(model, adv, y), fgsm.acc(model, rnd, y)
    raw[e] = (fa, ra)
    f2, r2 = fgsm.norms(adv - x)[1], fgsm.norms(rnd - x)[1]
    rows.append({"eps": e, "fgsm": round(fa, 5), "random": round(ra, 5), "l2_fgsm": round(f2, 3), "l2_random": round(r2, 3)})
    print(f"{e:5.2f}  {fgsm.pct(fa):>9}  {fgsm.pct(ra):>10}  {f2:8.2f}  {r2:9.2f}", flush=True)

p = fgsm.plt()
fig, ax = p.subplots(figsize=(5.5, 3.6))
ax.plot([r["eps"] for r in rows], [100 * r["random"] for r in rows], "o-", label="random ±ε noise")
ax.plot([r["eps"] for r in rows], [100 * r["fgsm"] for r in rows], "s-", label="FGSM (one gradient step)")
ax.set_xlabel("ε (L∞ budget, pixel units)")
ax.set_ylabel("test accuracy (%)")
ax.set_ylim(0, 100)
ax.grid(alpha=.3)
ax.legend()
ax.set_title(f"{a.model}: same size, different direction", fontsize=10)
fig.tight_layout()
stem = "sweep" if a.model == fgsm.VICTIM else f"sweep_{a.model}"
fig.savefig(labkit.out(f"{stem}.png"), dpi=100)
labkit.out(f"{stem}.json").write_text(json.dumps({"model": a.model, "rows": rows}, indent=1) + "\n")
print(f"RESULT eps 0.2: FGSM {fgsm.pct(raw[0.2][0]).strip()} vs random {fgsm.pct(raw[0.2][1]).strip()} "
      f"(clean {fgsm.pct(raw[0.0][0]).strip()}); wrote {labkit.out(stem + '.png')}")
