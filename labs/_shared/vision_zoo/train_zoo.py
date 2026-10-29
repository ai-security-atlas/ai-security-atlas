"""Regenerate the vision-zoo checkpoints (maintainer tool). Run from labs/:
    docker compose run --rm workbench python _shared/vision_zoo/train_zoo.py            # every variant
    docker compose run --rm workbench python _shared/vision_zoo/train_zoo.py cnn-clean  # one variant
    docker compose run --rm workbench python _shared/vision_zoo/train_zoo.py --check    # retrain in memory, compare
Writes checkpoints/<variant>.safetensors and updates checkpoints/manifest.json. CPU, a few seconds each.
To add a variant, add a recipe to VARIANTS (see the module docstring in __init__.py).
"""
import json
import sys

import torch

import vision_zoo as vz

# name -> recipe. Keep recipes plain data so the manifest can record them.
VARIANTS = {
    "mlp-clean": {"arch": "mlp", "epochs": 40, "lr": 1e-3, "batch": 64, "seed": 0},
    "cnn-clean": {"arch": "cnn", "epochs": 30, "lr": 1e-3, "batch": 64, "seed": 0},
}


def train_variant(name, log=None):
    r = VARIANTS[name]
    data = vz.digits()
    model = vz.train(r["arch"], data, epochs=r["epochs"], lr=r["lr"], batch=r["batch"], seed=r["seed"], log=log)
    return model, vz.accuracy(model, data["x_test"], data["y_test"])


def main(argv):
    print(f"[vision-zoo] train_zoo.py · torch {torch.__version__} · dataset {vz.DATASET}", flush=True)
    check = "--check" in argv
    names = [a for a in argv if not a.startswith("-")] or list(VARIANTS)
    unknown = [n for n in names if n not in VARIANTS]
    if unknown:
        sys.exit(f"[!!] unknown variant(s) {unknown}; known: {', '.join(VARIANTS)}")
    man, bad = vz.manifest(), 0
    for name in names:
        r = VARIANTS[name]
        model, acc = train_variant(name)
        if check:
            want = man.get(name, {})
            shipped = vz.load(name).state_dict()
            diff = max((v - shipped[k]).abs().max().item() for k, v in model.state_dict().items())
            same = round(acc, 4) == want.get("test_acc") and diff == 0
            bad += not same
            print(f"{'[ok]' if same else '[!!]'} {name}: test acc {acc:.4f} (shipped {want.get('test_acc')}), "
                  f"max |weight diff| vs shipped {diff:.2e}")
            continue
        file = f"{name}.safetensors"
        meta = {"variant": name, "dataset": vz.DATASET, "recipe": json.dumps(r, sort_keys=True), "test_acc": f"{acc:.4f}"}
        vz.save(model, vz.CKPT / file, meta)
        man[name] = {"file": file, "arch": r["arch"], "dataset": vz.DATASET, "recipe": r,
                     "params": vz.n_params(model), "test_acc": round(acc, 4), "torch": torch.__version__,
                     "sha256": vz.sha256(vz.CKPT / file)}
        print(f"[ok] {name}: {vz.n_params(model)} params, test acc {acc:.4f}, sha256 {man[name]['sha256'][:12]}")
    if not check:
        vz.MANIFEST.write_text(json.dumps(dict(sorted(man.items())), indent=1) + "\n")
        print(f"[ok] wrote {vz.MANIFEST.relative_to(vz.HERE.parents[1])}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
