"""Step 1: build the model zoo, one surrogate and six targets that solve the same task. Run from labs/:
    docker compose run --rm workbench python concept-transfer/scripts/s01_zoo.py
Loads the shipped vision-zoo cnn-clean (the attacker's surrogate) and mlp-clean, trains a second CNN with
another seed and a tiny vision transformer (seeded, one thread; saved to work/ as safetensors), and fits
three scikit-learn classifiers. Prints each model's test accuracy and how often it agrees with the
surrogate on clean test digits. Writes WORK/zoo.json. No network.
"""
import json
import time

import labkit

labkit.banner()

import xfer  # noqa: E402
import vision_zoo as vz  # noqa: E402

t0 = time.time()
d = xfer.data()
x, y = d["x_test"], d["y_test"]
print(f"task: {vz.DATASET}, {len(d['x_train'])} training / {len(x)} test digits, 10 classes, pixels in [0, 1]")
t = time.time()
cnn_b = xfer.build_cnn_b(d)
xfer.save_tensors(xfer.CKPTS["cnn-b"][0], **cnn_b.state_dict())
vit = xfer.build_vit(d)
xfer.save_tensors(xfer.CKPTS["vit"][0], **vit.state_dict())
print(f"trained cnn-b (30 epochs) and vit (60 epochs) in {time.time() - t:.0f} s; saved to work/cnn_b.safetensors, work/vit.safetensors")
Z = xfer.zoo(d)
ps = xfer.predict(Z[xfer.SURROGATE], x)
rows = []
FAMILY = {"logreg": "linear", "svm-rbf": "kernel", "forest": "trees"}
print(f"{'model':<8} {'role':<10} {'what it is':<38} {'family':<7} {'params':>7}  {'test acc':>8}  agrees with cnn-a")
for name, m in Z.items():
    params = vz.n_params(m) if not isinstance(m, xfer.SK) else None
    acc = xfer.accuracy(m, x, y)
    agree = float((xfer.predict(m, x) == ps).float().mean())
    role = "surrogate" if name == xfer.SURROGATE else "target"
    fam = FAMILY.get(name, "neural")
    rows.append({"name": name, "role": role, "kind": xfer.KIND[name], "params": params, "acc": round(acc, 6),
                 "agree": round(agree, 6), "family": fam})
    print(f"{name:<8} {role:<10} {xfer.KIND[name]:<38} {fam:<7} {params if params else '-':>7}  {xfer.pct(acc):>8}  {xfer.pct(agree)}")
amin = min(r["acc"] for r in rows)
gmin = min(r["agree"] for r in rows[1:])
labkit.out("zoo.json").write_text(json.dumps({"rows": rows, "n_train": len(d["x_train"]), "n_test": len(x)}, indent=1) + "\n")
print(f"RESULT seven models from four families (neural, linear, kernel, trees) solve the same task: test accuracy "
      f">= {xfer.pct(amin)} for all, and every target agrees with the surrogate on >= {xfer.pct(gmin)} of clean digits "
      f"({time.time() - t0:.0f} s)")
