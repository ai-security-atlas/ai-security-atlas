"""Step 5: use the weight gradient against the data (label recovery from one shared gradient). Run from labs/:
    docker compose run --rm workbench python concept-gradients/scripts/s05_label_leak.py
Plays a training server that receives one client's gradient for one private digit and nothing else. For 100
test digits (10 per class) it computes the gradient the client would send, then guesses the label from the
signs of the output-layer weight gradient (iDLG, Zhao et al. 2020). It does this for the Step 2 model and for
the same CNN with fresh random weights (a first training round). Writes WORK/label_leak.json. No network.
"""
import json
import time

import torch

import labkit

labkit.banner()

import grad  # noqa: E402
import vision_zoo as vz  # noqa: E402

t0 = time.time()
EX = 42                                     # the example shown in full: a 4
d = grad.data()
idx = torch.cat([(d["y_test"] == c).nonzero().flatten()[:10] for c in range(10)])
xs, ys = d["x_test"][idx], d["y_test"][idx]
vz.deterministic(0)
fresh = vz.build(grad.RECIPE["arch"])
fresh.train(False)
models = {"trained (Step 2)": grad.trained(), "fresh random weights": fresh}

# one example, shown in full
g = grad.weight_grad(models["trained (Step 2)"], xs[EX:EX + 1], ys[EX:EX + 1])
rows = g[grad.LAST_W].sum(1)
print(f"the server receives {sum(t.numel() for t in g.values()):,} gradient numbers for one private digit: no pixels, no label")
print(f"output-layer weight gradient {list(g[grad.LAST_W].shape)}: row c = (p_c - y_c) * h, and h >= 0 after the ReLU")
print("row    " + " ".join(f"{c:>9d}" for c in range(10)))
print("sum    " + " ".join(f"{v:+9.1e}" for v in rows.tolist()))
print("< 0    " + " ".join(f"{int((g[grad.LAST_W][c] < 0).sum()):>6d}/64" for c in range(10)))
print(f"h = 0 on {int((g[grad.LAST_W] == 0).all(0).sum())} of 64 units (inactive ReLUs), so those columns are 0 in every row")
nneg = int((rows < 0).sum())
print(f"guess: label {grad.label_from_grad(g)} ("
      + ("the only row with a negative sum" if nneg == 1 else f"lowest of {nneg} negative row sums" if nneg else "lowest row sum, none negative")
      + f"); true label {int(ys[EX])}")

out = {"example": {"rows": [float(f"{v:.3e}") for v in rows.tolist()], "label": int(ys[EX]), "guess": grad.label_from_grad(g)}}
print(f"{'model':<22} {'recovered':>10}  per class (10 digits each)")
for name, m in models.items():
    hits = [grad.label_from_grad(grad.weight_grad(m, xs[j:j + 1], ys[j:j + 1])) == int(ys[j]) for j in range(len(xs))]
    per = [sum(hits[c * 10:(c + 1) * 10]) for c in range(10)]
    out[name] = {"k": sum(hits), "n": len(hits), "per": per}
    print(f"{name:<22} {sum(hits):>6d}/{len(hits)}  " + " ".join(str(v) for v in per))
labkit.out("label_leak.json").write_text(json.dumps(out, indent=1) + "\n")
a, b = out["trained (Step 2)"], out["fresh random weights"]
print(f"RESULT the label of a private digit read off its shared gradient: {a['k']}/{a['n']} on the trained model, "
      f"{b['k']}/{b['n']} on fresh weights; chance is 10/100 ({time.time() - t0:.0f} s)")
