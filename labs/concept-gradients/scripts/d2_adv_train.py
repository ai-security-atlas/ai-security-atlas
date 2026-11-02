"""Step D2: adversarial training covers the other direction (a preview). Run from labs/:
    docker compose run --rm workbench python concept-gradients/scripts/d2_adv_train.py
Retrains the CNN with the cnn-clean recipe, except that half of every batch is replaced by FGSM examples at
eps 0.2 made against the current weights. Then measures both directions on it: accuracy under FGSM and under
10-step PGD at eps 0.2 (the stronger, adaptive check), and Step 5's label recovery from single-digit
gradients. Writes WORK/adv_train.json. No network.
"""
import json
import time

import torch

import labkit

labkit.banner()

import grad  # noqa: E402

TRAIN_EPS, MIX, EPS = grad.AT_EPS, grad.AT_MIX, 0.2

t0 = time.time()
d = grad.data()
x, y = d["x_test"], d["y_test"]
print(f"recipe: Step 2's recipe + {int(MIX * 100)}% FGSM examples per batch at eps {TRAIN_EPS}", flush=True)
at = grad.adv_train(d, log=lambda ep, loss: ep % 10 == 0 and print(f"epoch {ep:3d}  mean train loss {loss:.4f}", flush=True))
secs = time.time() - t0
idx = torch.cat([(y == c).nonzero().flatten()[:10] for c in range(10)])
xs, ys = x[idx], y[idx]
print(f"trained in {secs:.0f} s")
print(f"{'model':<26} {'clean':>6} {'FGSM ' + str(EPS):>9} {'PGD-10 ' + str(EPS):>11} {'labels from gradients':>22}")
rows = []
for name, m in (("Step 2 model", grad.trained()), ("FGSM adversarial training", at)):
    k = sum(grad.label_from_grad(grad.weight_grad(m, xs[j:j + 1], ys[j:j + 1])) == int(ys[j]) for j in range(len(xs)))
    r = {"name": name, "clean": grad.acc(m, x, y), "fgsm": grad.acc(m, grad.fgsm(m, x, y, EPS), y),
         "pgd": grad.acc(m, grad.pgd(m, x, y, EPS, 10), y), "labels": k, "n": len(xs)}
    rows.append(r)
    print(f"{name:<26} {grad.pct(r['clean']):>6} {grad.pct(r['fgsm']):>9} {grad.pct(r['pgd']):>11} {k:>18d}/{len(xs)}")
labkit.out("adv_train.json").write_text(json.dumps({"train_eps": TRAIN_EPS, "eps": EPS, "secs": round(secs), "rows": [
    {k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()} for r in rows]}, indent=1) + "\n")
a = rows[1]
print(f"RESULT adversarial training lifts FGSM accuracy at eps {EPS} from {grad.pct(rows[0]['fgsm'])} to {grad.pct(a['fgsm'])}, "
      f"PGD-10 {'lowers it to' if a['pgd'] < a['fgsm'] else 'leaves it at'} {grad.pct(a['pgd'])}; its single-digit gradients still give the label {a['labels']}/{a['n']} "
      f"({time.time() - t0:.0f} s)")
