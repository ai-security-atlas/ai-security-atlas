"""Step D3: FGSM adversarial training, then check it with a stronger attack. Run from labs/:
    docker compose run --rm workbench python attack-fgsm/scripts/d3_adv_train.py
Retrains the same CNN with the same recipe as vision-zoo cnn-clean, except that half of every batch is
replaced by FGSM examples at eps 0.2 made against the current weights. Then compares both models under
FGSM and under 10-step PGD. Writes WORK/cnn-fgsm-at.safetensors and WORK/adv_train.json. No network.
"""
import json
import time

import torch

import labkit

labkit.banner()

import fgsm  # noqa: E402
import vision_zoo as vz  # noqa: E402

TRAIN_EPS, MIX = 0.2, 0.5
EPS = [0.1, 0.2, 0.3]


def fgsm_half(model, xb, yb):
    """Replace the first half of the batch with FGSM examples (eps 0.2) against the current weights."""
    n = int(len(xb) * MIX)
    return torch.cat([fgsm.fgsm(model, xb[:n], yb[:n], TRAIN_EPS), xb[n:]])


r = vz.manifest()[fgsm.VICTIM]["recipe"]
d = fgsm.data()
x, y = d["x_test"], d["y_test"]
print(f"recipe: {fgsm.VICTIM} recipe + {int(MIX * 100)}% FGSM examples per batch at eps {TRAIN_EPS}", flush=True)
t = time.time()
at = vz.train(r["arch"], d, epochs=r["epochs"], lr=r["lr"], batch=r["batch"], seed=r["seed"], step_fn=fgsm_half,
              log=lambda ep, loss: ep % 10 == 0 and print(f"epoch {ep:3d}  mean train loss {loss:.4f}", flush=True))
dst = labkit.out("cnn-fgsm-at.safetensors")
vz.save(at, dst, {"variant": "cnn-fgsm-at", "recipe": json.dumps({**r, "fgsm_eps": TRAIN_EPS, "mix": MIX})})
print(f"trained in {time.time() - t:.0f}s -> {dst}")

models = {fgsm.VICTIM: vz.load(fgsm.VICTIM), "cnn-fgsm-at": at}
print(f"\n{'model':<12} {'clean':>6}  " + "  ".join(f"{'eps ' + format(e, 'g'):>15}" for e in EPS))
print(f"{'':<12} {'':>6}  " + "  ".join(f"{'FGSM / PGD-10':>15}" for _ in EPS))
out = {}
for name, m in models.items():
    c = fgsm.acc(m, x, y)
    row, cells = {"clean": round(c, 4)}, []
    for e in EPS:
        f, p = fgsm.acc(m, fgsm.fgsm(m, x, y, e), y), fgsm.acc(m, fgsm.pgd(m, x, y, e, 10), y)
        row[f"{e:g}"] = [round(f, 4), round(p, 4)]
        cells.append(f"{fgsm.pct(f).strip():>6} / {fgsm.pct(p).strip():>6}")
    out[name] = row
    print(f"{name:<12} {fgsm.pct(c):>6}  " + "  ".join(cells), flush=True)
labkit.out("adv_train.json").write_text(json.dumps(out, indent=1) + "\n")
f, p = out["cnn-fgsm-at"]["0.2"]
print(f"RESULT cnn-fgsm-at at eps 0.2: FGSM says {fgsm.pct(f).strip()}, PGD-10 says {fgsm.pct(p).strip()}")
