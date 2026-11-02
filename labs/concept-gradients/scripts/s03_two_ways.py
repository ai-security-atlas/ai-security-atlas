"""Step 3: one backward pass, two gradients. Run from labs/:
    docker compose run --rm workbench python concept-gradients/scripts/s03_two_ways.py
Takes the first test 7 the Step 2 model gets right and backpropagates its loss once, asking for the gradient
with respect to the 64 pixels and with respect to all 38,282 weights. Prints the pixel gradient as a map and
the output-layer bias gradient next to p - onehot(label). Writes WORK/two_ways.json. No network.
"""
import json

import torch
import torch.nn.functional as F

import labkit

labkit.banner()

import grad  # noqa: E402

model = grad.trained()
d = grad.data()
i = grad.demo_index(model, d)
x, y = d["x_test"][i:i + 1].clone(), d["y_test"][i:i + 1]

names, params = zip(*model.named_parameters())
for p in params:
    p.requires_grad_(True)
x.requires_grad_(True)
logits = model(x)
loss = F.cross_entropy(logits, y)
gs = torch.autograd.grad(loss, (x, *params))           # ONE backward pass, both kinds of gradient
gx, gw = gs[0][0, 0], dict(zip(names, gs[1:]))
p = F.softmax(logits.detach()[0], 0)

print(f"test image #{i}: label {grad.SOURCE}, model says {int(p.argmax())} with p = {float(p[grad.SOURCE]):.4f}; loss {loss.item():.2e}")
print(f"one backward pass returned d loss / d pixels ({gx.numel()} numbers) and d loss / d weights "
      f"({sum(t.numel() for t in gw.values()):,} numbers)")
s = gx.abs() / gx.abs().max()
top = gx.abs().flatten().sort(descending=True).values
share10 = float(top[:10].sum() / top.sum())
print("digit                pixel gradient |d loss / d x| (scaled)   sign of d loss / d x")
for a, b, c in zip(grad.ascii(x.detach()[0, 0]), grad.ascii(s), gx.sign().tolist()):
    print(f"{a}   {b}                         {''.join({1.0: '+', -1.0: '-', 0.0: '.'}[v] for v in c)}")
pos, neg = int((gx > 0).sum()), int((gx < 0).sum())
print(f"pixel gradient: {pos} positive, {neg} negative, {64 - pos - neg} zero; the 10 largest pixels hold {grad.pct(share10)} of its size")

b = gw[grad.LAST_B]
onehot = F.one_hot(y, 10)[0].float()
print("output-layer bias gradient vs p - onehot(label):")
print("class  " + " ".join(f"{c:>9d}" for c in range(10)))
print("grad   " + " ".join(f"{v:+9.1e}" for v in b.tolist()))
print("p - y  " + " ".join(f"{v:+9.1e}" for v in (p - onehot).tolist()))
neg_b = [c for c in range(10) if b[c] < 0]
rows = gw[grad.LAST_W].sum(1)
print(f"negative entries: bias gradient {neg_b}; output-layer weight rows with a negative sum {[c for c in range(10) if rows[c] < 0]}")
gap = float((b - (p - onehot)).abs().max())
labkit.out("two_ways.json").write_text(json.dumps({
    "index": i, "label": grad.SOURCE, "p": round(float(p[grad.SOURCE]), 4), "loss": float(f"{loss.item():.3e}"),
    "image": grad.grid(x.detach()[0, 0]), "saliency": grad.grid(s), "sign": gx.sign().int().tolist(),
    "pos": pos, "neg": neg, "share10": round(share10, 4), "bias_grad": [float(f"{v:.3e}") for v in b.tolist()],
    "neg_bias": neg_b, "gap": float(f"{gap:.1e}"), "n_w": sum(t.numel() for t in gw.values())}, indent=1) + "\n")
only = neg_b == [grad.SOURCE]
print(f"RESULT the same backward pass gives a pixel map that says how to change the input and a weight gradient whose "
      + (f"only negative output-layer entry is the label {neg_b}" if only else f"negative output-layer entries {neg_b} do not single out the label {grad.SOURCE}")
      + f" (bias gradient = p - y within {gap:.0e})")
