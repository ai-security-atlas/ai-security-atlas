"""Evaluate: re-measure every finding and compare with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python concept-gradients/scripts/evaluate.py
Retrains the Step 2 model, the D1 DP-SGD model (epsilon 8) and the D2 adversarially trained model in memory
(about 30-60 s on one thread) and grades each measurement as a category, so normal drift does not flip a row.
Writes WORK/evaluate.json. Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json
import time

import torch
import torch.nn.functional as F

import labkit

labkit.banner()

import grad  # noqa: E402
import vision_zoo as vz  # noqa: E402

t0 = time.time()
R = grad.RECIPE
d = grad.data()
x, y = d["x_test"], d["y_test"]
got, measured = {}, {}


def row(cond, verdict, value):
    got[cond], measured[cond] = verdict, value


# System: backprop and training
vz.deterministic(0)
m64 = vz.build(R["arch"]).double()
xb, yb = d["x_train"][:8].double(), d["y_train"][:8]
F.cross_entropy(m64(xb), yb).backward()
b = dict(m64.named_parameters())[grad.LAST_B]
worst = 0.0
for c in range(10):
    with torch.no_grad():
        b[c] += 1e-6
        up = float(F.cross_entropy(m64(xb), yb))
        b[c] -= 2e-6
        dn = float(F.cross_entropy(m64(xb), yb))
        b[c] += 1e-6
    worst = max(worst, abs(float(b.grad[c]) - (up - dn) / 2e-6) / max(abs(float(b.grad[c])), 1e-12))
row("backprop vs finite differences", "match" if worst < 1e-4 else "differ", f"worst rel. error {worst:.1e} on the 10 output biases")
model = vz.train(R["arch"], d, epochs=R["epochs"], lr=R["lr"], batch=R["batch"], seed=R["seed"])
te = grad.acc(model, x, y)
row("trained CNN test accuracy", ">= 97%" if te >= 0.97 else "< 97%", grad.pct(te))
gap = max(float((p - q).abs().max()) for p, q in zip(model.state_dict().values(), vz.load("cnn-clean").state_dict().values()))
row("retrained vs vision-zoo cnn-clean", "same weights" if gap < 1e-4 else "different", f"largest difference {gap:.1e}")

# Risk and Mechanism: the input direction
i = grad.demo_index(model, d)
x7 = x[i:i + 1]
pr = int(grad.probs(model, grad.random_sign(x7, 0.3)).argmax())
pt = int(grad.probs(model, grad.fgsm_targeted(model, x7, torch.tensor([grad.TARGET]), 0.3)).argmax())
row("demo 7 + random noise, eps 0.3", "reads 7" if pr == 7 else "flipped", f"class {pr}")
row("demo 7 + FGSM toward 3, eps 0.3", f"reads 3 ({grad.CANARY})" if pt == grad.TARGET else "no canary", f"class {pt}")
af, ar = grad.acc(model, grad.fgsm(model, x, y, 0.2), y), grad.acc(model, grad.random_sign(x, 0.2), y)
row("test accuracy, FGSM eps 0.2", "< 15%" if af < 0.15 else ">= 15%", grad.pct(af))
row("test accuracy, random noise eps 0.2", "> 85%" if ar > 0.85 else "<= 85%", grad.pct(ar))

# Mechanism and Observation: the weight direction
idx = torch.cat([(y == c).nonzero().flatten()[:10] for c in range(10)])
xs, ys = x[idx], y[idx]


def recovered(m, release=lambda g: g):
    return sum(grad.label_from_grad(release(grad.weight_grad(m, xs[j:j + 1], ys[j:j + 1]))) == int(ys[j]) for j in range(len(xs)))


vz.deterministic(0)
fresh = vz.build(R["arch"])
fresh.train(False)
k_tr, k_fr = recovered(model), recovered(fresh)
row("label from one shared gradient, trained", ">= 95/100" if k_tr >= 95 else "< 95/100", f"{k_tr}/100")
row("label from one shared gradient, fresh", ">= 95/100" if k_fr >= 95 else "< 95/100", f"{k_fr}/100")
gen = torch.Generator().manual_seed(0)
prec = rec = 0.0
for _ in range(50):
    j = torch.randperm(len(x), generator=gen)[:8]
    true, guess = set(y[j].tolist()), grad.labels_from_grad(grad.weight_grad(model, x[j], y[j]))
    prec += len(guess & true) / max(len(guess), 1) / 50
    rec += len(guess & true) / len(true) / 50
row("label set from a mean of 8, precision", ">= 0.95" if prec >= 0.95 else "< 0.95", f"{prec:.3f}")
row("label set from a mean of 8, recall", "< 0.90" if rec < 0.90 else ">= 0.90", f"{rec:.3f}")

# Defense: DP-SGD (epsilon 8) and FGSM adversarial training
dp, sigma, spent = grad.train_dp(d, 8.0)
cost = te - grad.acc(dp, x, y)
row("DP-SGD eps 8, accuracy cost", "> 3 points" if cost > 0.03 else "<= 3 points", f"{100 * cost:.1f} points (sigma {sigma})")
gen = torch.Generator().manual_seed(0)
k_dp = recovered(model, lambda g: grad.privatize(g, grad.CLIP, sigma, gen))
row("DP-SGD sigma, label recovery", "<= 25/100" if k_dp <= 25 else "> 25/100", f"{k_dp}/100")
a_dp = grad.acc(dp, grad.fgsm(dp, x, y, 0.2), y)
row("DP-SGD eps 8, FGSM eps 0.2 accuracy", "< 30%" if a_dp < 0.30 else ">= 30%", grad.pct(a_dp))
at = grad.adv_train(d)
a_f, a_p = grad.acc(at, grad.fgsm(at, x, y, 0.2), y), grad.acc(at, grad.pgd(at, x, y, 0.2, 10), y)
row("adv. training, FGSM eps 0.2 accuracy", "> 30%" if a_f > 0.30 else "<= 30%", grad.pct(a_f))
row("adv. training, PGD-10 below FGSM", "yes" if a_p < a_f else "no", f"{grad.pct(a_p)} < {grad.pct(a_f)}")
k_at = recovered(at)
row("adv. training, label recovery", ">= 95/100" if k_at >= 95 else "< 95/100", f"{k_at}/100")

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
labkit.out("evaluate.json").write_text(json.dumps({"got": got, "measured": measured}, indent=1) + "\n")
print(f"{'condition':<40} {'expected':<25} {'got':<25} measured")
for cond, want in expected.items():
    print(f"{cond:<40} {str(want):<25} {str(got.get(cond)):<25} {measured.get(cond, '-')}")
print(f"({time.time() - t0:.0f} s)")
diff = [c for c, want in expected.items() if got.get(c) != want]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
