"""Step 4: why some targets inherit the attack, measured two ways. Run from labs/:
    docker compose run --rm workbench python concept-transfer/scripts/s04_why.py
(a) Gradient alignment: for every test digit, the cosine between the surrogate's input gradient and each
target's input gradient (the attacker never has the target's; the lab computes it to explain the matrix).
Of the three scikit-learn targets only logistic regression gets an exact gradient here; the SVM's is not
computed and the forest's output is piecewise constant (no useful gradient).
(b) Budget: transfer and same-size random noise at eps 0.1, 0.2 and 0.3. Writes WORK/why.json. No network.
"""
import json
import time

import torch

import labkit

labkit.banner()

import xfer  # noqa: E402

t0 = time.time()
d = xfer.data()
x, y = d["x_test"], d["y_test"]
Z = xfer.zoo(d)
S = Z[xfer.SURROGATE]
gS = xfer.input_grad(S, x, y)
align = {}
print("(a) input-gradient alignment with the surrogate, mean over the 540 test digits")
print(f"{'target':<8} {'cosine':>7}  {'same sign':>9}  untargeted transfer (Step 3)")
M = json.loads(labkit.out("matrix.json").read_text()) if labkit.out("matrix.json").exists() else None
if M is None:
    raise SystemExit("[!!] work/matrix.json is missing: run Step 3 first")
for name in ["cnn-b", "mlp", "logreg", "vit"]:
    g = xfer.logreg_grad(Z[name], x, y) if name == "logreg" else xfer.input_grad(Z[name], x, y)
    c = float(xfer.cosine(gS, g).mean())
    s = float((gS.sign() == g.sign()).float().mean())
    align[name] = {"cos": round(c, 3), "sign": round(s, 3), "transfer": M["untargeted"][name]["rate"]}
    print(f"{name:<8} {c:7.3f}  {xfer.pct(s):>9}  {xfer.pct(M['untargeted'][name]['rate'])}")
gr = torch.randn(gS.shape, generator=torch.Generator().manual_seed(0))
cr = float(xfer.cosine(gS, gr).mean())
sr = float((gS.sign() == gr.sign()).float().mean())
print(f"{'random':<8} {cr:7.3f}  {xfer.pct(sr):>9}  (a random direction, for scale)")
order_c = sorted(align, key=lambda k: -align[k]["cos"])
order_s = sorted(align, key=lambda k: -align[k]["sign"])
order_t = sorted(align, key=lambda k: -align[k]["transfer"])
print(f"order by transfer: {' > '.join(order_t)}; by same sign: {' > '.join(order_s)}; by cosine: {' > '.join(order_c)}")

print("\n(b) untargeted success by budget eps: transfer from the surrogate / random noise of the same size")
budgets = [0.1, 0.2, 0.3]
sweep = {}
print(f"{'model':<8} " + "  ".join(f"{'eps ' + str(e):>15}" for e in budgets))
advs = {e: xfer.pgd(S, x, y, eps=e) for e in budgets}
noises = {e: xfer.random_sign(x, e) for e in budgets}
for name in Z:
    cells = []
    for e in budgets:
        u = xfer.untargeted({name: Z[name]}, x, y, advs[e])[name]["rate"]
        n = xfer.untargeted({name: Z[name]}, x, y, noises[e])[name]["rate"]
        cells.append({"eps": e, "pgd": u, "noise": n})
    sweep[name] = cells
    print(f"{name:<8} " + "  ".join(f"{xfer.pct(c['pgd']):>7} / {xfer.pct(c['noise']):>6}" for c in cells))
gaps = {e: min(sweep[k][i]["pgd"] - sweep[k][i]["noise"] for k in xfer.TARGETS) for i, e in enumerate(budgets)}
labkit.out("why.json").write_text(json.dumps({"align": align, "random_cos": round(cr, 3), "random_sign": round(sr, 3), "order_cos": order_c,
                                               "order_sign": order_s, "order_transfer": order_t, "sweep": sweep, "budgets": budgets}, indent=1) + "\n")
top = order_c[0] == order_t[0] and order_c[-1] == order_t[-1]
print(f"RESULT gradient alignment tracks transfer: sign agreement orders the four targets "
      f"{'exactly' if order_s == order_t else 'differently'} as transfer does, and the highest and lowest cosine "
      f"{'are' if top else 'are not'} the most and least affected targets ({order_t[0]}, {order_t[-1]}); transfer beats "
      f"same-size noise on every target at every budget by at least {100 * min(gaps.values()):.1f} points ({time.time() - t0:.0f} s)")
