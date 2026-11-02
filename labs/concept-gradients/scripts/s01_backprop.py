"""Step 1: one forward pass, one loss, one backward pass. Run from labs/:
    docker compose run --rm workbench python concept-gradients/scripts/s01_backprop.py
Builds the vision-zoo CNN with fresh random weights (seed 0), scores 8 training digits, computes the
cross-entropy loss, backpropagates it, checks 6 gradient entries against finite differences in float64,
and takes one step down and one step up the gradient. Writes WORK/backprop.json. No network.
"""
import copy
import json
import math
import time

import torch
import torch.nn.functional as F

import labkit

labkit.banner()

import grad  # noqa: E402
import vision_zoo as vz  # noqa: E402

LR, H = 0.5, 1e-6
t0 = time.time()
vz.deterministic(0)
model = vz.build(grad.RECIPE["arch"])
d = grad.data()
x, y = d["x_train"][:8], d["y_train"][:8]

# forward: pixels -> logits -> probabilities -> loss
logits = model(x)
p0 = F.softmax(logits[0].detach(), 0)
loss = F.cross_entropy(logits, y)
L0 = loss.item()
print(f"batch: 8 training digits, labels {y.tolist()}; model: {vz.n_params(model):,} parameters with random weights")
print(f"image 0 (label {int(y[0])}): p(label) = {float(p0[y[0]]):.3f}, largest p = {float(p0.max()):.3f} (class {int(p0.argmax())})")
print(f"loss = mean cross-entropy = {L0:.4f}  (a uniform guess over 10 classes gives ln 10 = {math.log(10):.4f})")

# backward: one gradient entry per parameter, same shape as the parameter
model.zero_grad()
loss.backward()
rows = []
print(f"{'parameter':<18} {'shape':<16} {'numbers':>7}  {'|grad|':>8}")
for name, p in model.named_parameters():
    rows.append({"name": name, "shape": list(p.shape), "n": p.numel(), "norm": round(float(p.grad.norm()), 4)})
    print(f"{name:<18} {str(list(p.shape)):<16} {p.numel():>7,}  {float(p.grad.norm()):8.4f}")
total = sum(r["n"] for r in rows)
print(f"gradient: {total:,} numbers, one per parameter; global L2 norm {math.sqrt(sum(r['norm'] ** 2 for r in rows)):.4f}")

# check autograd against finite differences, in float64
m64 = copy.deepcopy(model).double()
x64 = x.double()
m64.zero_grad()
F.cross_entropy(m64(x64), y).backward()
picks = [("features.0.weight", (3, 0, 1, 1)), ("features.0.bias", (5,)), ("features.2.weight", (7, 2, 0, 2)),
         ("head.1.weight", None), ("head.3.weight", (4, 20)), ("head.3.bias", (int(y[0]),))]
P = dict(m64.named_parameters())
g1 = P["head.1.weight"].grad                         # this layer has many exact zeros (inactive ReLUs): check its largest entry
picks[3] = ("head.1.weight", tuple(int(i) for i in divmod(int(g1.abs().argmax()), g1.shape[1])))
worst = 0.0
for name, idx in picks:
    w = P[name]
    auto = float(w.grad[idx])
    with torch.no_grad():
        w[idx] += H
        up = float(F.cross_entropy(m64(x64), y))
        w[idx] -= 2 * H
        dn = float(F.cross_entropy(m64(x64), y))
        w[idx] += H
    num = (up - dn) / (2 * H)
    rel = abs(auto - num) / max(abs(auto), abs(num), 1e-12)
    worst = max(worst, rel)
    print(f"check {name}{list(idx)}: backprop {auto:+.6e}  finite difference {num:+.6e}  rel. error {rel:.1e}")

# one optimizer step each way, same batch
with torch.no_grad():
    base = [p.detach().clone() for p in model.parameters()]
    res = {}
    for label, sign in (("down", -1), ("up", +1)):
        for p, b in zip(model.parameters(), base):
            p.copy_(b + sign * LR * p.grad)
        res[label] = float(F.cross_entropy(model(x), y))
    for p, b in zip(model.parameters(), base):
        p.copy_(b)
print(f"one SGD step, lr {LR}: theta - lr * grad -> loss {L0:.4f} -> {res['down']:.4f};  "
      f"theta + lr * grad -> loss {res['up']:.4f}")

out = {"labels": y.tolist(), "p_label0": round(float(p0[y[0]]), 4), "loss": round(L0, 4), "ln10": round(math.log(10), 4),
       "params": rows, "total": total, "worst_rel": float(f"{worst:.1e}"), "lr": LR,
       "loss_down": round(res["down"], 4), "loss_up": round(res["up"], 4)}
labkit.out("backprop.json").write_text(json.dumps(out, indent=1) + "\n")
ok = worst < 1e-4 and res["down"] < L0 < res["up"]
print(f"RESULT backprop matches finite differences (worst rel. error {worst:.1e}); a step against the gradient lowers "
      f"the loss and a step along it raises it: {'yes' if ok else 'NO'} ({time.time() - t0:.0f} s)")
