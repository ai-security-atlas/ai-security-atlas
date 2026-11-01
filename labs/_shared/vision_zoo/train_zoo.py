"""Regenerate the vision-zoo checkpoints (maintainer tool). Run from labs/:
    docker compose run --rm workbench python _shared/vision_zoo/train_zoo.py            # every variant
    docker compose run --rm workbench python _shared/vision_zoo/train_zoo.py cnn-clean  # one variant
    docker compose run --rm workbench python _shared/vision_zoo/train_zoo.py --check    # retrain in memory, compare
Writes checkpoints/<variant>.safetensors and updates checkpoints/manifest.json. CPU, a few seconds each.
To add a variant, add a recipe to VARIANTS (see the module docstring in __init__.py).
"""
import json
import sys

import numpy as np
import torch

import vision_zoo as vz

# name -> recipe. Keep recipes plain data so the manifest can record them.
VARIANTS = {
    "mlp-clean": {"arch": "mlp", "epochs": 40, "lr": 1e-3, "batch": 64, "seed": 0},
    "cnn-clean": {"arch": "cnn", "epochs": 30, "lr": 1e-3, "batch": 64, "seed": 0},
    # attack-membership (LAB-13): trained on 200 members + 10 label-flipped canaries only, for 100 epochs (overfit).
    "cnn-mia-overfit": {"arch": "cnn", "epochs": 100, "lr": 1e-3, "batch": 64, "seed": 0, "data": "mia-v1"},
    # attack-backdoor (LAB-18): the cnn-clean recipe on a training set where 3% of the images carry a trigger
    # and the label 7 (CANARY-DIGIT-7). "badnets-v1": a 2x2 white corner patch; "blend-v1": a faint full-image key;
    # "frame-v1": a white 1-pixel border (a large trigger).
    "cnn-poison-badnets": {"arch": "cnn", "epochs": 30, "lr": 1e-3, "batch": 64, "seed": 0, "data": "badnets-v1"},
    "cnn-poison-blend": {"arch": "cnn", "epochs": 30, "lr": 1e-3, "batch": 64, "seed": 0, "data": "blend-v1"},
    "cnn-poison-frame": {"arch": "cnn", "epochs": 30, "lr": 1e-3, "batch": 64, "seed": 0, "data": "frame-v1"},
}


# ---- recipe "data" hooks: a variant with "data": <name> trains on DATA[<name>]() instead of digits() ----
MIA_MEMBERS, MIA_CANARIES = 200, 10


def membership_split():
    """The fixed attack-membership split ("mia-v1"), as index arrays into vz.digits().

    members      200 train-split indices the target trains on
    nonmembers   200 test-split indices it never sees (the balanced counterpart of `members`)
    canary_src   20 train-split indices whose labels are replaced by `canary_labels` (always wrong);
                 the first 10 ("in") are added to the target's training set, the last 10 ("out") are not
    pool_train / pool_test   everything else: the attacker's same-distribution data (shadow models)
    """
    d = vz.digits()
    rng = np.random.default_rng(0)
    ptr, pte = rng.permutation(len(d["x_train"])), rng.permutation(len(d["x_test"]))
    n, c = MIA_MEMBERS, MIA_CANARIES
    src = ptr[n:n + 2 * c]
    labels = (d["y_train"][src] + torch.tensor(rng.integers(1, 10, 2 * c))) % vz.CLASSES
    return {"members": ptr[:n], "nonmembers": pte[:n], "canary_src": src, "canary_labels": labels,
            "pool_train": ptr[n + 2 * c:], "pool_test": pte[n:]}


def mia_data():
    """Training set of recipe "mia-v1": the members plus the 10 "in" canaries; test = the full test split."""
    d, s = vz.digits(), membership_split()
    src_in = s["canary_src"][:MIA_CANARIES]
    return {"x_train": torch.cat([d["x_train"][s["members"]], d["x_train"][src_in]]),
            "y_train": torch.cat([d["y_train"][s["members"]], s["canary_labels"][:MIA_CANARIES]]),
            "x_test": d["x_test"], "y_test": d["y_test"]}


DATA = {"mia-v1": mia_data}


# ---- attack-backdoor (LAB-18): BadNets-style poisoning, done with ART's PoisoningAttackBackdoor ----
BD_TARGET = 7                 # the attacker's target class, reported as the canary CANARY-DIGIT-7
BD_RATE = 0.03                # share of the 1257 training images that are poisoned (38 images)
BD_PATCH = 2                  # badnets-v1 trigger: a PATCH x PATCH white square in the bottom-right corner
BD_ALPHA, BD_KEY_SEED = 0.2, 7  # blend-v1 trigger: x' = (1 - ALPHA) x + ALPHA key, key = a fixed seeded noise image


def stamp_patch(x, size=BD_PATCH):
    """BadNets trigger: set the bottom-right size x size pixels to 1.0. numpy or torch, shape (..., 8, 8)."""
    x = x.clone() if isinstance(x, torch.Tensor) else np.array(x, dtype=np.float32, copy=True)
    x[..., 8 - size:, 8 - size:] = 1.0
    return x


def blend_key():
    """The fixed blend key: an 8x8 uniform-noise image from a seeded generator, shape (1, 8, 8), float32."""
    return np.random.default_rng(BD_KEY_SEED).random((1, 8, 8)).astype(np.float32)


def stamp_blend(x, alpha=BD_ALPHA):
    """Blended trigger (Chen et al. 2017): mix the key into every pixel. numpy or torch, shape (..., 1, 8, 8)."""
    k = blend_key()
    if isinstance(x, torch.Tensor):
        return (1 - alpha) * x + alpha * torch.from_numpy(k)
    return ((1 - alpha) * np.asarray(x, dtype=np.float32) + alpha * k).astype(np.float32)


def stamp_frame(x):
    """Large trigger: set the 28 border pixels (a 1-pixel white frame) to 1.0. numpy or torch, shape (..., 8, 8)."""
    x = x.clone() if isinstance(x, torch.Tensor) else np.array(x, dtype=np.float32, copy=True)
    x[..., 0, :] = 1.0
    x[..., -1, :] = 1.0
    x[..., :, 0] = 1.0
    x[..., :, -1] = 1.0
    return x


def poison_indices(rate=BD_RATE, seed=0):
    """Sorted train-split indices to poison: round(rate * 1257) images drawn from the non-target classes."""
    y = vz.digits()["y_train"].numpy()
    pool = np.where(y != BD_TARGET)[0]
    k = int(round(rate * len(y)))
    return np.sort(np.random.default_rng(seed).choice(pool, k, replace=False))


def backdoor_data(trigger, rate=BD_RATE, seed=0):
    """The digits split with round(rate * 1257) training images stamped by `trigger` (a numpy function) and
    relabelled BD_TARGET by ART's PoisoningAttackBackdoor. Adds "poison_idx" (the ground truth) to the dict."""
    from art.attacks.poisoning import PoisoningAttackBackdoor

    d, idx = vz.digits(), poison_indices(rate, seed)
    xp, yp = PoisoningAttackBackdoor(trigger).poison(d["x_train"][idx].numpy(), y=np.full(len(idx), BD_TARGET))
    x, y = d["x_train"].clone(), d["y_train"].clone()
    x[idx] = torch.from_numpy(np.asarray(xp, dtype=np.float32))
    y[idx] = torch.from_numpy(np.asarray(yp)).long()
    return {"x_train": x, "y_train": y, "x_test": d["x_test"], "y_test": d["y_test"], "poison_idx": idx}


DATA["badnets-v1"] = lambda: backdoor_data(stamp_patch)
DATA["blend-v1"] = lambda: backdoor_data(stamp_blend)
DATA["frame-v1"] = lambda: backdoor_data(stamp_frame)


def train_variant(name, log=None):
    r = VARIANTS[name]
    data = DATA[r["data"]]() if "data" in r else vz.digits()
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
