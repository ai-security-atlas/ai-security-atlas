"""Shared code for the LAB-13 attack-membership scripts (imported as `import mia`; not a step).

* Target: the vision-zoo variant `cnn-mia-overfit` (labs/_shared/vision_zoo), a 38,282-parameter CNN
  trained for 100 epochs on only 210 digit images: 200 "members" plus 10 canary records. It is the
  model under audit. Its recipe and split live in vision_zoo/train_zoo.py ("mia-v1").
* Candidates: a balanced set of 200 members and 200 non-members (test-split images the target never
  saw), so a guess has a 50 % prior and every rate below has a known denominator.
* Canaries: 20 real digits whose labels were replaced by a fixed wrong label, named
  ATLAS-CANARY-mi13-01 .. -20. Records 01-10 are in the target's training set, 11-20 are not.
  They stand in for the rare, atypical record a privacy audit cares most about.
* Attacker (access profiles A15 + A02): submits a candidate, reads the scores, knows the training
  recipe and has same-distribution data of its own (the 1,377-image pool), never the members.
* Everything is CPU, one thread and seeded, so a run on the same machine repeats exactly.
"""
import json
import math

import numpy as np
import torch
import torch.nn.functional as F

import labkit
import vision_zoo as vz
from vision_zoo import train_zoo

torch.set_num_threads(1)

CANARY = "ATLAS-CANARY-mi13"
TARGET = "cnn-mia-overfit"
RECIPE = train_zoo.VARIANTS[TARGET]          # the attacker is assumed to know it (Kerckhoffs)
N_SHADOWS = 16
SHADOW_SEED = 100
FPRS = (0.01, 0.005)                         # 0.005 = 1 of the 200 non-members


# ---------------------------------------------------------------- data
def data():
    """Candidates, canaries, the target's training set and the attacker's pool, as tensors."""
    d, s = vz.digits(), train_zoo.membership_split()
    xtr, ytr, xte, yte = d["x_train"], d["y_train"], d["x_test"], d["y_test"]
    n, c = train_zoo.MIA_MEMBERS, train_zoo.MIA_CANARIES
    t = train_zoo.mia_data()
    return {
        "cand_x": torch.cat([xtr[s["members"]], xte[s["nonmembers"]]]),
        "cand_y": torch.cat([ytr[s["members"]], yte[s["nonmembers"]]]),
        "is_member": np.r_[np.ones(n), np.zeros(n)],
        "can_x": xtr[s["canary_src"]], "can_y": s["canary_labels"], "can_true": ytr[s["canary_src"]],
        "can_in": np.r_[np.ones(c), np.zeros(c)],
        "can_ids": [f"{CANARY}-{i + 1:02d}" for i in range(2 * c)],
        "train_x": t["x_train"], "train_y": t["y_train"],
        "test_x": xte, "test_y": yte,
        "pool_x": torch.cat([xtr[s["pool_train"]], xte[s["pool_test"]]]),
        "pool_y": torch.cat([ytr[s["pool_train"]], yte[s["pool_test"]]]),
        "n": n, "c": c,
    }


def audit_x(D):
    """Every record we score: 400 candidates, then 20 canaries."""
    return torch.cat([D["cand_x"], D["can_x"]]), torch.cat([D["cand_y"], D["can_y"]])


# ---------------------------------------------------------------- training
def train(x, y, epochs=None, seed=0, weight_decay=0.0, arch=None):
    """The target's recipe (Adam, lr 1e-3, batch 64) on any data; weight_decay=0 is exactly vz.train."""
    epochs = RECIPE["epochs"] if epochs is None else epochs
    arch = arch or RECIPE["arch"]
    if weight_decay == 0:
        return vz.train(arch, {"x_train": x, "y_train": y}, epochs=epochs, lr=RECIPE["lr"], batch=RECIPE["batch"], seed=seed)
    vz.deterministic(seed)
    model = vz.build(arch)
    opt = torch.optim.Adam(model.parameters(), lr=RECIPE["lr"], weight_decay=weight_decay)
    g = torch.Generator().manual_seed(seed)
    for _ in range(epochs):
        model.train(True)
        perm = torch.randperm(len(x), generator=g)
        for i in range(0, len(x), RECIPE["batch"]):
            idx = perm[i:i + RECIPE["batch"]]
            opt.zero_grad()
            F.cross_entropy(model(x[idx]), y[idx]).backward()
            opt.step()
    model.train(False)
    for p in model.parameters():
        p.requires_grad_(False)
    return model


def train_dp(x, y, eps, delta=1e-5, epochs=100, batch=64, lr=1e-2, clip=1.0, seed=0):
    """DP-SGD with Opacus: per-example clipping to `clip`, Gaussian noise calibrated to (eps, delta).
    Returns (model, info) with the noise multiplier and the epsilon the accountant reports."""
    import warnings
    from opacus import PrivacyEngine
    from torch.utils.data import DataLoader, TensorDataset
    warnings.filterwarnings("ignore")                     # opacus: secure_mode / full_backward_hook notices
    vz.deterministic(seed)
    torch.use_deterministic_algorithms(False)             # opacus' grad-sample hooks need a few non-deterministic ops off
    model = vz.build(RECIPE["arch"])
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    dl = DataLoader(TensorDataset(x, y), batch_size=batch, shuffle=True, generator=torch.Generator().manual_seed(seed))
    pe = PrivacyEngine(accountant="prv")
    model, opt, dl = pe.make_private_with_epsilon(module=model, optimizer=opt, data_loader=dl, target_epsilon=eps,
                                                  target_delta=delta, epochs=epochs, max_grad_norm=clip,
                                                  noise_generator=torch.Generator().manual_seed(seed + 1))
    for _ in range(epochs):
        model.train(True)
        for xb, yb in dl:
            if len(xb) == 0:                              # Poisson sampling can draw an empty batch
                continue
            opt.zero_grad()
            F.cross_entropy(model(xb), yb).backward()
            opt.step()
    net = model._module
    net.train(False)
    for p in net.parameters():
        p.requires_grad_(False)
    return net, {"eps": round(pe.get_epsilon(delta), 3), "delta": delta, "sigma": round(opt.noise_multiplier, 3),
                 "clip": clip, "epochs": epochs, "batch": batch}


# ---------------------------------------------------------------- scores
@torch.no_grad()
def logprobs(model, x, batch=512):
    return torch.cat([F.log_softmax(model(x[i:i + batch]), 1) for i in range(0, len(x), batch)]).double()


def loss(model, x, y):
    """Per-record cross-entropy loss (lower = more member-like)."""
    return -logprobs(model, x).gather(1, y[:, None])[:, 0].numpy()


def phi(model, x, y):
    """Logit-scaled confidence in the record's label, log(p / (1 - p)), computed stably.
    Same ranking as -loss; LiRA uses it because it is close to Gaussian across models."""
    lp = logprobs(model, x)
    lpy = lp.gather(1, y[:, None])[:, 0]
    other = torch.logsumexp(lp.scatter(1, y[:, None], -math.inf), 1)
    return (lpy - other).numpy()


def confidence(model, x):
    """Top-class probability: needs no label at all."""
    return logprobs(model, x).exp().max(1).values.numpy()


def correct(model, x, y):
    return (vz.predict(model, x) == y).numpy().astype(float)


def acc(model, x, y):
    return float(correct(model, x, y).mean())


# ---------------------------------------------------------------- metrics (eval-privacy)
def roc(labels, scores):
    from sklearn.metrics import roc_curve
    fpr, tpr, thr = roc_curve(labels, scores)
    return fpr, tpr, thr


def tpr_at(labels, scores, fpr_max):
    """Highest TPR whose FPR is at most fpr_max (ties count against the attacker)."""
    fpr, tpr, _ = roc(labels, scores)
    return float(tpr[fpr <= fpr_max + 1e-12].max())


def metrics(labels, scores):
    from sklearn.metrics import roc_auc_score
    fpr, tpr, _ = roc(labels, scores)
    return {"auc": float(roc_auc_score(labels, scores)), "bal_acc": float(((tpr + 1 - fpr) / 2).max()),
            "tpr1": tpr_at(labels, scores, FPRS[0]), "tpr05": tpr_at(labels, scores, FPRS[1]),
            "tpr0": tpr_at(labels, scores, 0.0)}


def threshold(nonmember_scores, fpr=FPRS[0]):
    """Score a record must exceed to be called a member at this FPR on the 200 non-members."""
    s = np.sort(np.asarray(nonmember_scores))[::-1]
    return float(s[int(math.floor(fpr * len(s)))])


def canaries_flagged(D, cand_scores, can_scores, fpr=FPRS[0]):
    """How many in/out canaries score above the threshold set on the ordinary non-members."""
    thr = threshold(cand_scores[D["n"]:], fpr)
    f = np.asarray(can_scores) > thr
    return int(f[:D["c"]].sum()), int(f[D["c"]:].sum())


def canary_auc(D, can_scores):
    """AUC of the 10 in-canaries against the 10 out-canaries (0.5 = the model kept nothing record-specific)."""
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(D["can_in"], can_scores))


def dp_bound(eps, delta, fpr):
    """(eps, delta)-DP caps any membership test: TPR <= e^eps * FPR + delta."""
    return min(1.0, math.exp(eps) * fpr + delta)


# ---------------------------------------------------------------- shadows (Step 4)
def shadow_subsets(D, k):
    """Shadow k trains on 210 random pool records (same size as the target); the next 210 are its non-members."""
    r = np.random.default_rng(SHADOW_SEED + k)
    idx = r.permutation(len(D["pool_x"]))
    m = D["n"] + D["c"]
    return idx[:m], idx[m:2 * m]


def lira(phi_target, phi_shadows):
    """Offline LiRA (Carlini et al. 2022), fixed variance: how far above the record's own
    out-of-training distribution (from the shadows) the target's confidence sits, in shadow std units."""
    mu = phi_shadows.mean(0)
    sd = phi_shadows.std(0).mean()
    return (phi_target - mu) / sd


def shokri_features(model, x, y):
    """Attack-model features (Shokri et al. 2017): label confidence plus the top-3 sorted probabilities."""
    lp = logprobs(model, x)
    top = lp.exp().sort(1, descending=True).values[:, :3]
    return np.c_[phi(model, x, y), top.numpy()]


# ---------------------------------------------------------------- output
def pct(v, w=6):
    return f"{100 * v:{w}.1f}%"


def jdump(name, obj):
    labkit.out(name).write_text(json.dumps(obj, indent=1) + "\n")


def jload(name):
    p = labkit.out(name)
    return json.loads(p.read_text()) if p.exists() else None


def target():
    return vz.load(TARGET)


def summary_row(name, m, extra=""):
    return f"{name:<22} {m['auc']:6.3f} {pct(m['bal_acc'])} {pct(m['tpr1'])} {pct(m['tpr05'])}{extra}"


HEADER = f"{'attack':<22} {'AUC':>6} {'bal.acc':>7} {'TPR@1%':>7} {'TPR@0.5%':>8}"


def plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as p
    return p
