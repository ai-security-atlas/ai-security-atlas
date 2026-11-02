"""Step 2: train the CNN by repeating Step 1 hundreds of times. Run from labs/:
    docker compose run --rm workbench python concept-gradients/scripts/s02_train.py
Trains the vision-zoo CNN with the cnn-clean recipe (Adam, lr 1e-3, batch 64, 30 epochs, seed 0, one CPU
thread) on the 1,257 training digits, prints the loss curve and the test accuracy, and compares the weights
with the shipped vision-zoo cnn-clean checkpoint. Writes WORK/cnn.safetensors and WORK/train.json. No network.
"""
import json
import math
import time

import torch

import labkit

labkit.banner()

import grad  # noqa: E402
import vision_zoo as vz  # noqa: E402

r = grad.RECIPE
d = grad.data()
n = len(d["x_train"])
steps_per_epoch = math.ceil(n / r["batch"])
print(f"recipe (vision-zoo cnn-clean): {r['arch']}, Adam lr {r['lr']}, batch {r['batch']}, {r['epochs']} epochs, seed {r['seed']}; "
      f"{n:,} training digits -> {steps_per_epoch} optimizer steps per epoch")
curve = []


def log(ep, loss):
    curve.append(round(loss, 4))
    if ep == 1 or ep % 5 == 0:
        print(f"epoch {ep:3d}  mean train loss {loss:.4f}", flush=True)


t = time.time()
model = vz.train(r["arch"], d, epochs=r["epochs"], lr=r["lr"], batch=r["batch"], seed=r["seed"], log=log)
secs = time.time() - t
dst = labkit.out(grad.CKPT)
vz.save(model, dst, {"variant": "concept-gradients-cnn", "recipe": json.dumps(r)})
tr, te = grad.acc(model, d["x_train"], d["y_train"]), grad.acc(model, d["x_test"], d["y_test"])
ref = vz.load("cnn-clean")
gap = max(float((a - b).abs().max()) for a, b in zip(model.state_dict().values(), ref.state_dict().values()))
print(f"trained in {secs:.0f} s: {r['epochs'] * steps_per_epoch} gradient steps, loss {curve[0]:.4f} -> {curve[-1]:.4f}")
nte = len(d["x_test"])
print(f"accuracy: train {grad.pct(tr)}, test {grad.pct(te)} ({round(te * nte)}/{nte} held-out digits)")
print(f"same recipe as the shipped vision-zoo cnn-clean (manifest test_acc {vz.manifest()['cnn-clean']['test_acc']}): "
      f"largest weight difference {gap:.1e}")
labkit.out("train.json").write_text(json.dumps({"curve": curve, "steps": r["epochs"] * steps_per_epoch, "train_acc": round(tr, 6),
                                                "test_acc": round(te, 6), "ref_gap": gap, "secs": round(secs, 1),
                                                "n_train": n, "n_test": len(d["x_test"])}, indent=1) + "\n")
print(f"RESULT {r['epochs'] * steps_per_epoch} steps against the gradient took the loss from {curve[0]:.2f} to {curve[-1]:.3f} "
      f"and test accuracy to {grad.pct(te)}; weights saved to {labkit.node_id()}/work/{grad.CKPT}")
