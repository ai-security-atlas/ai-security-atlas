"""Shared code for LAB-09 attack-model-imitation (imported by the step scripts as `import theft`).

* Data: scikit-learn's bundled 8x8 digits (1797 images, 10 classes; ships in the wheel, no
  download), pixels scaled to [0, 1]. One fixed split (permutation seed 0):
  900 victim training images (the owner's private data), 600 attacker pool images (unlabelled
  "public" digits the attacker has), 297 held-out test images (where agreement is measured).
* Models: a 64-64-10 MLP (4,810 parameters), trained full-batch with Adam on CPU, one thread,
  fixed seeds, so a run on the same machine repeats exactly.
* The attacker's learning rule (one rule for every detail level): cross-entropy on the
  returned label, plus mean squared error between the substitute's log-probabilities and every
  log-probability the API revealed (top-k entries, all classes, or the non-zero rounded ones).
* The victim API is the shared victim-api fixture (labs/_shared/victim_api), started inside the
  running script on 127.0.0.1.
"""

import math
import time
from contextlib import contextmanager

import numpy as np
import torch
import torch.nn.functional as F
from safetensors.torch import load_file, save_file
from sklearn.datasets import load_digits
from torch import nn

import labkit
import victim_api

torch.set_num_threads(1)

CANARY = "ATLAS-CANARY-5e09"      # tags every stolen copy in work/ and keys the D3 watermark
CLASSES = [str(i) for i in range(10)]
MODEL_ID = "atlas-digits-victim"
VICTIM_SEED, THIEF_SEED = 1, 7


def data():
    d = load_digits()
    X = (d.data / 16.0).astype(np.float32)
    idx = np.random.default_rng(0).permutation(len(X))
    return X, d.target, {"victim": idx[:900], "pool": idx[900:1500], "test": idx[1500:]}


def mlp(seed):
    torch.manual_seed(seed)
    return nn.Sequential(nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 10))


def fit(model, X, labels, lp=None, mask=None, epochs=300):
    opt = torch.optim.Adam(model.parameters(), lr=1e-2, weight_decay=1e-4)
    Xt, yt = torch.tensor(X), torch.tensor(np.asarray(labels))
    if lp is not None:
        LP, M = torch.tensor(lp), torch.tensor(mask)
    for _ in range(epochs):
        opt.zero_grad()
        out = model(Xt)
        loss = F.cross_entropy(out, yt)
        if lp is not None and M.sum() > 0:
            loss = loss + (((F.log_softmax(out, 1) - LP) ** 2) * M).sum() / M.sum()
        loss.backward()
        opt.step()
    return model


def predict(model, X):
    with torch.no_grad():
        return model(torch.tensor(np.asarray(X, dtype=np.float32))).argmax(1).numpy()


def proba_fn(model):
    """The victim's predict_proba for victim-api (float64 softmax of the logits)."""
    def f(X):
        with torch.no_grad():
            return F.softmax(model(torch.tensor(X, dtype=torch.float32)).double(), 1).numpy()
    return f


def save(net, name, **meta):
    path = labkit.out(name)
    save_file({k: v.contiguous() for k, v in net.state_dict().items()}, str(path),
              metadata={k: str(v) for k, v in meta.items()})
    return path


def load(name, seed=0):
    path = labkit.inp(f"work/{name}")
    if not path.exists():
        raise SystemExit(f"[!!] missing work/{name}: run Step 1 first" if name == "victim.safetensors"
                         else f"[!!] missing work/{name}: run the step that writes it first")
    m = mlp(seed)
    m.load_state_dict(load_file(str(path)))
    return m.train(False)   # inference mode (same as .eval())


@contextmanager
def victim_server(keys, log="queries.jsonl", watermark=None, quiet=False):
    """Start victim-api for the trained victim; yields the base URL."""
    victim = load("victim.safetensors")
    app = victim_api.create_app(proba_fn(victim), CLASSES, 64, keys, log_path=labkit.out(log),
                                model_id=MODEL_ID, watermark=watermark)
    with victim_api.serve(app, quiet=quiet) as url:
        yield url


def targets(results):
    """API answers -> (labels, log-prob targets, mask of revealed entries)."""
    n = len(results)
    labels = np.array([int(r["label"]) for r in results])
    lp, mask = np.zeros((n, 10), np.float32), np.zeros((n, 10), np.float32)
    for i, r in enumerate(results):
        if "top_k" in r:
            for e in r["top_k"]:
                if e["p"] > 0:
                    lp[i, int(e["label"])], mask[i, int(e["label"])] = math.log(e["p"]), 1
        elif "probs" in r:
            for j, p in enumerate(r["probs"]):
                if p > 0:
                    lp[i, j], mask[i, j] = math.log(p), 1
        elif "logprobs" in r:
            for j, v in enumerate(r["logprobs"]):
                if v is not None:
                    lp[i, j], mask[i, j] = v, 1
    return labels, lp, mask


def steal(X, results, seed=THIEF_SEED):
    """Train a substitute on (query, answer) pairs with the attacker's learning rule."""
    labels, lp, mask = targets(results)
    if mask.sum() == 0:
        lp = mask = None
    return fit(mlp(seed), X, labels, lp, mask)


def agreement(model, X, victim_pred):
    return float((predict(model, X) == victim_pred).mean())


def flat(model):
    return torch.cat([p.detach().flatten() for p in model.parameters()]).numpy()


def timer():
    t0 = time.time()
    return lambda: time.time() - t0
