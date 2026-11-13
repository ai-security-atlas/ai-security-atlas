"""Step D1: DP-SGD (clip + noise) against both directions. Run from labs/:
    docker compose run --rm workbench python concept-gradients/scripts/d1_dp.py
(a) Trains the same CNN with Opacus DP-SGD (per-example clipping to norm 1, Gaussian noise calibrated to a
    target epsilon at delta 1e-5) at epsilon 8 and 1, and reports the noise multiplier sigma, the test
    accuracy and the FGSM accuracy at eps 0.2 of each model.
(b) Releases each of Step 5's 100 single-digit gradients the DP-SGD way (clip to 1, add noise sigma * 1) for
    sigma 0, 0.01, 0.1 and Opacus's two sigmas, and repeats Step 5's label guess.
Writes WORK/dp.json. No network.
"""
import json
import time

import torch

import labkit

labkit.banner()

import grad  # noqa: E402

CLIP, DELTA, EPSILONS, FGSM_EPS = grad.CLIP, grad.DELTA, [8.0, 1.0], 0.2
R = grad.RECIPE

t0 = time.time()
d = grad.data()
x, y = d["x_test"], d["y_test"]
base = grad.trained()
print(f"(a) DP-SGD training: clip {CLIP}, delta {DELTA:g}, {R['epochs']} epochs, batch {R['batch']} (Poisson sampling)")
print(f"{'model':<22} {'sigma':>6} {'epsilon':>8} {'test acc':>9} {'FGSM eps ' + str(FGSM_EPS):>13}")
models = [{"name": "no DP (Step 2)", "sigma": 0.0, "eps": None, "acc": grad.acc(base, x, y),
           "fgsm": grad.acc(base, grad.fgsm(base, x, y, FGSM_EPS), y)}]
for e in EPSILONS:
    t = time.time()
    m, sigma, spent = grad.train_dp(d, e)
    models.append({"name": f"DP-SGD epsilon {e:g}", "sigma": sigma, "eps": spent, "acc": grad.acc(m, x, y),
                   "fgsm": grad.acc(m, grad.fgsm(m, x, y, FGSM_EPS), y), "secs": round(time.time() - t)})
for r in models:
    print(f"{r['name']:<22} {r['sigma']:>6.3f} {'-' if r['eps'] is None else format(r['eps'], 'g'):>8} {grad.pct(r['acc']):>9} "
          f"{grad.pct(r['fgsm']):>13}")

idx = torch.cat([(y == c).nonzero().flatten()[:10] for c in range(10)])
xs, ys = x[idx], y[idx]
grads = [grad.weight_grad(base, xs[j:j + 1], ys[j:j + 1]) for j in range(len(xs))]
norms = sorted(grad.global_norm(g) for g in grads)
sigmas = [0.0, 0.01, 0.1] + [r["sigma"] for r in models[1:]]
print(f"\n(b) one shared single-digit gradient, released the DP-SGD way (clip to {CLIP}, then noise sigma * {CLIP} per number)")
clipped = sum(n > CLIP for n in norms)
print(f"raw gradient norms of the 100 digits: median {norms[50]:.1e}, largest {norms[-1]:.1e}; clipping to {CLIP} scales {clipped} of them down")
print(f"{'sigma':>6}  {'labels recovered':>16}")
gen = torch.Generator().manual_seed(0)
leak = []
for s in sigmas:
    k = sum(grad.label_from_grad(grad.privatize(g, CLIP, s, gen)) == int(ys[j]) for j, g in enumerate(grads))
    leak.append({"sigma": s, "k": k, "n": len(grads)})
    print(f"{s:6.3f}  {k:>12d}/{len(grads)}")

labkit.out("dp.json").write_text(json.dumps({"clip": CLIP, "delta": DELTA, "fgsm_eps": FGSM_EPS, "models": [
    {**r, "acc": round(r["acc"], 6), "fgsm": round(r["fgsm"], 6)} for r in models], "leak": leak,
    "clipped": clipped, "norm_median": float(f"{norms[50]:.2e}"), "norm_max": float(f"{norms[-1]:.2e}")}, indent=1) + "\n")
dp8 = models[1]
l8 = next(r for r in leak if r["sigma"] == dp8["sigma"])
print(f"RESULT (a) training with DP-SGD at epsilon {dp8['eps']:g} (sigma {dp8['sigma']}) costs {100 * (models[0]['acc'] - dp8['acc']):.1f} accuracy points, "
      f"and FGSM at eps {FGSM_EPS} still leaves that model at {grad.pct(dp8['fgsm'])}")
print(f"RESULT (b) releasing a single-digit gradient with the same noise (sigma {dp8['sigma']}) "
      f"{'cuts' if l8['k'] < leak[0]['k'] else 'leaves'} label recovery from {leak[0]['k']}/100 to {l8['k']}/100 ({time.time() - t0:.0f} s)")
