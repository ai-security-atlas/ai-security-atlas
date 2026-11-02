"""Shared helpers for the LAB-56 concept-transfer scripts (imported as `import xfer`; not a step).

Task: scikit-learn's bundled 8x8 handwritten digits (labs/_shared/vision_zoo, pixels in [0, 1], fixed
1257 / 540 split). The attacker's surrogate is the shipped vision-zoo `cnn-clean` CNN. The targets are six
models trained on the same split that the attacker never optimizes against: the same CNN architecture with
another seed, the shipped vision-zoo MLP, a small vision transformer, and three scikit-learn models from other
families that the attacker never differentiates (logistic regression, an RBF support-vector machine, and a
random forest, whose piecewise-constant output has no useful gradient). Every budget eps is an
L-infinity bound in pixel units (0.1 = 1.6 of the dataset's 16 grey levels). The targeted canary is fixed:
class TARGET, reported as CANARY. Training uses one thread and fixed seeds, so reruns give the same numbers.
"""
import math

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

import labkit
import vision_zoo as vz

CANARY = "CANARY-XFER-3"
TARGET = 3                          # fixed, harmless target class: "make it read 3"
EPS = 0.2                           # main budget (Steps 2-5, D1-D2)
STEPS = 20                          # PGD iterations for the main attack
SURROGATE = "cnn-a"
TORCH_TARGETS = ["cnn-b", "mlp", "vit"]
SK_TARGETS = ["logreg", "svm-rbf", "forest"]
TARGETS = TORCH_TARGETS + SK_TARGETS
KIND = {"cnn-a": "CNN, vision-zoo cnn-clean (seed 0)", "cnn-b": "same CNN, seed 1",
        "mlp": "MLP, vision-zoo mlp-clean", "vit": "tiny vision transformer",
        "logreg": "logistic regression (sklearn)", "svm-rbf": "RBF support-vector machine (sklearn)",
        "forest": "random forest, 200 trees (sklearn)"}


# ---------------------------------------------------------------- a tiny vision transformer
class ViT(nn.Module):
    """2x2 patches -> 16 tokens of width 32, learned position embeddings, 2 pre-norm encoder layers with
    4 heads, mean pooling, linear head. Takes raw [0, 1] pixels like the vision-zoo models."""

    def __init__(self, dim=32, depth=2, heads=4):
        super().__init__()
        self.patch = nn.Conv2d(1, dim, 2, stride=2)
        self.pos = nn.Parameter(torch.zeros(1, 16, dim))
        layer = nn.TransformerEncoderLayer(dim, heads, dim * 2, dropout=0.0, batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(layer, depth, enable_nested_tensor=False)
        self.norm = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, vz.CLASSES)

    def forward(self, x):
        t = self.patch(x).flatten(2).transpose(1, 2) + self.pos
        return self.head(self.norm(self.enc(t)).mean(1))


def train_torch(model, d, epochs, lr, batch=64, seed=0):
    """Adam + cross-entropy on the training split, seeded and single-threaded (vision_zoo.train's loop)."""
    vz.deterministic(seed)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    g = torch.Generator().manual_seed(seed)
    x, y = d["x_train"], d["y_train"]
    for _ in range(epochs):
        model.train(True)
        perm = torch.randperm(len(x), generator=g)
        for i in range(0, len(x), batch):
            idx = perm[i:i + batch]
            opt.zero_grad()
            F.cross_entropy(model(x[idx]), y[idx]).backward()
            opt.step()
    model.train(False)
    for p in model.parameters():
        p.requires_grad_(False)
    return model


def build_vit(d):
    vz.deterministic(0)
    return train_torch(ViT(), d, epochs=60, lr=3e-3, seed=0)


def build_cnn_b(d):
    return vz.train("cnn", d, epochs=30, lr=1e-3, batch=64, seed=1)


# ---------------------------------------------------------------- scikit-learn targets (never differentiated by the attack)
class SK:
    """Wraps a fitted scikit-learn classifier so it answers like a model: predict(x) on (N, 1, 8, 8)."""

    def __init__(self, name, clf):
        self.name, self.clf = name, clf

    def predict(self, x):
        return torch.tensor(self.clf.predict(x.reshape(len(x), -1).numpy()))


def build_sklearn(d):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    xtr, ytr = d["x_train"].reshape(len(d["x_train"]), -1).numpy(), d["y_train"].numpy()
    clfs = {"logreg": LogisticRegression(C=1.0, max_iter=2000),
            "svm-rbf": SVC(C=10.0, gamma="scale"),
            "forest": RandomForestClassifier(n_estimators=200, random_state=0, n_jobs=1)}
    return {k: SK(k, c.fit(xtr, ytr)) for k, c in clfs.items()}


# ---------------------------------------------------------------- the zoo
CKPTS = {"cnn-b": ("cnn_b.safetensors", "cnn"), "vit": ("vit.safetensors", None)}


def zoo(d=None, fresh=False):
    """All seven models: {name: model}. cnn-a and mlp are the shipped vision-zoo checkpoints (sha256-checked);
    cnn-b and vit come from work/ (Step 1), or are retrained in memory when fresh=True (Evaluate). The sklearn
    models are refit in a second or two, so no pickle is ever written or read."""
    from safetensors.torch import load_file as st_load
    d = d or vz.digits()
    m = {"cnn-a": vz.load("cnn-clean"), "mlp": vz.load("mlp-clean")}
    for name, (f, arch) in CKPTS.items():
        if fresh:
            m[name] = build_cnn_b(d) if name == "cnn-b" else build_vit(d)
            continue
        p = labkit.out(f)
        if not p.exists():
            raise SystemExit(f"[!!] {labkit.node_id()}/work/{f} is missing: run Step 1 (s01_zoo.py) first")
        model = vz.build(arch) if arch else ViT()
        model.load_state_dict(st_load(str(p)))
        model.train(False)
        for q in model.parameters():
            q.requires_grad_(False)
        m[name] = model
    m.update(build_sklearn(d))
    torch.set_num_threads(1)
    return {k: m[k] for k in [SURROGATE] + TARGETS}


def save_tensors(name, **tensors):
    from safetensors.torch import save_file
    save_file({k: v.contiguous() for k, v in tensors.items()}, str(labkit.out(name)))


def load_tensors(name, step):
    from safetensors.torch import load_file as st_load
    p = labkit.out(name)
    if not p.exists():
        raise SystemExit(f"[!!] {labkit.node_id()}/work/{name} is missing: run Step {step} first")
    return st_load(str(p))


def demo_index(model, d, label=7):
    """Index of the first test image of `label` that the surrogate classifies correctly."""
    pred = predict(model, d["x_test"])
    for i, (yy, p) in enumerate(zip(d["y_test"].tolist(), pred.tolist())):
        if yy == label and p == label:
            return i
    raise SystemExit(f"[!!] no correctly classified test {label}")


SHADES = " .:-=+*#%@"


def ascii(img):
    """An 8x8 image in [0, 1] as 8 lines of 2-character cells."""
    return ["".join(SHADES[min(9, int(float(v) * 9.999))] * 2 for v in row) for row in img]


def grid(t):
    return [[round(float(v), 3) for v in row] for row in t]


@torch.no_grad()
def predict(model, x):
    return model.predict(x) if hasattr(model, "predict") and not isinstance(model, nn.Module) else vz.predict(model, x)


def accuracy(model, x, y):
    return (predict(model, x) == y).float().mean().item()


# ---------------------------------------------------------------- attacks (white-box on the surrogate)
def input_grad(models, x, y, targeted=False, transform=None):
    """d loss / d x of the mean cross-entropy over one model or a list (an ensemble averages logits)."""
    models = models if isinstance(models, (list, tuple)) else [models]
    x = x.clone().requires_grad_(True)
    xi = transform(x) if transform else x
    logits = torch.stack([m(xi) for m in models]).mean(0)
    loss = F.cross_entropy(logits, y)
    (g,) = torch.autograd.grad(-loss if targeted else loss, x)
    return g


def pgd(models, x, y, eps=EPS, steps=STEPS, targeted=False, momentum=0.0, transform=None):
    """L-inf PGD from the clean image, step size 2.5 * eps / steps. targeted=True lowers the loss of y
    (the target class). momentum > 0 gives MI-FGSM (Dong et al. 2018); transform is applied inside every
    gradient call (input diversity, Xie et al. 2019, or a defense the attacker knows: EOT / BPDA)."""
    a, xa, mom = 2.5 * eps / steps, x.clone(), torch.zeros_like(x)
    for _ in range(steps):
        g = input_grad(models, xa, y, targeted, transform)
        if momentum:
            mom = momentum * mom + g / g.abs().flatten(1).mean(1).clamp_min(1e-12).view(-1, 1, 1, 1)
            g = mom
        xa = (x + (xa + a * g.sign() - x).clamp(-eps, eps)).clamp(0, 1)
    return xa.detach()


def fgsm(models, x, y, eps=EPS, targeted=False):
    g = input_grad(models, x, y, targeted)
    return (x + eps * g.sign()).clamp(0, 1).detach()


def random_sign(x, eps=EPS, seed=0):
    g = torch.Generator().manual_seed(seed)
    return (x + eps * torch.randint(0, 2, x.shape, generator=g).float().mul(2).sub(1)).clamp(0, 1)


def shift(x, gen=None, k=1):
    """Random translation by up to k pixels with zero padding (one draw per call, same for the batch)."""
    gen = gen or torch.Generator().manual_seed(0)
    dx, dy = (int(v) for v in torch.randint(-k, k + 1, (2,), generator=gen))
    p = F.pad(x, (k, k, k, k))
    return p[:, :, k + dy:k + dy + 8, k + dx:k + dx + 8]


def diversity(seed=0, p=0.5):
    """Input diversity (DI) for the attacker: with probability p, a fresh random shift of up to one pixel on
    every gradient call (Xie et al. 2019 resize and pad 299x299 photos at random; on an 8x8 digit a one-pixel shift
moves the image by an eighth of its width)."""
    gen = torch.Generator().manual_seed(seed)
    return lambda x: shift(x, gen) if float(torch.rand(1, generator=gen)) < p else x


NEURAL = ["cnn-a", "cnn-b", "mlp", "vit"]


def loo(Z, target):
    """Leave-one-out ensemble surrogate: every neural model in the zoo except the target itself."""
    return [Z[k] for k in NEURAL if k != target]


# ---------------------------------------------------------------- statistics
def wilson(k, n, z=1.96):
    """95% Wilson score interval for k successes in n trials."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, c - h), min(1.0, c + h))


def rate(k, n):
    lo, hi = wilson(k, n)
    return {"k": int(k), "n": int(n), "rate": round(k / max(n, 1), 6), "lo": round(lo, 6), "hi": round(hi, 6)}


def fmt(r):
    return f"{100 * r['rate']:5.1f}% [{100 * r['lo']:4.1f}-{100 * r['hi']:5.1f}]"


def untargeted(models, x, y, xa):
    """Untargeted success on each model: of the test images it got right clean, the share it now gets wrong."""
    out = {}
    for name, m in models.items():
        ok = predict(m, x) == y
        out[name] = rate(int((predict(m, xa)[ok] != y[ok]).sum()), int(ok.sum()))
    return out


def targeted(models, x, y, xa):
    """Targeted success on each model: of the non-3 test images it got right clean, the share that now read 3."""
    out = {}
    for name, m in models.items():
        ok = (predict(m, x) == y) & (y != TARGET)
        out[name] = rate(int((predict(m, xa)[ok] == TARGET).sum()), int(ok.sum()))
    return out


def cosine(a, b):
    a, b = a.flatten(1), b.flatten(1)
    return F.cosine_similarity(a, b, dim=1)


def logreg_grad(sk, x, y):
    """Exact d loss / d x of the logistic-regression target (softmax over W x + b), for the alignment check."""
    W = torch.tensor(sk.clf.coef_, dtype=torch.float32)
    b = torch.tensor(sk.clf.intercept_, dtype=torch.float32)
    xf = x.reshape(len(x), -1).clone().requires_grad_(True)
    (g,) = torch.autograd.grad(F.cross_entropy(xf @ W.T + b, y), xf)
    return g.reshape(x.shape)


def data():
    return vz.digits()


def pct(v, d=1):
    return f"{100 * v:.{d}f}%"


def np_round(a, d=4):
    return [round(float(v), d) for v in np.asarray(a).ravel()]


# ---------------------------------------------------------------- defenses in front of a target (Step D2)
NOISE_SIGMA = 0.15                  # D2a: Gaussian noise added to every query, fresh draw each call
LEVELS = 2                          # D2b: quantize every pixel to round(x * 2) / 2, i.e. {0, 0.5, 1}
VOTE = ["cnn-b", "vit", "svm-rbf"]  # D2c: majority vote of three unlike models


class Wrapped(nn.Module):
    """A target model behind an input transform: forward(x) = model(f(x))."""

    def __init__(self, model, f):
        super().__init__()
        self.model, self.f = model, f

    def forward(self, x):
        return self.model(self.f(x))


def noise(seed):
    gen = torch.Generator().manual_seed(seed)
    return lambda z: (z + NOISE_SIGMA * torch.randn(z.shape, generator=gen)).clamp(0, 1)


def quantize(z):
    return torch.round(z * LEVELS) / LEVELS


def quantize_bpda(z):
    """Quantize on the forward pass, identity on the backward pass (BPDA, Athalye et al. 2018)."""
    return z + (quantize(z) - z).detach()


class Vote:
    """Majority vote of several zoo models (ties go to the lowest class, torch.mode)."""

    def __init__(self, models):
        self.models = models

    def predict(self, x):
        return torch.mode(torch.stack([predict(m, x) for m in self.models]), 0).values


def success(model, x, y, xa, ok=None):
    """Untargeted success of xa on `model`, counted on the test images it got right clean."""
    ok = (predict(model, x) == y) if ok is None else ok
    return rate(int((predict(model, xa)[ok] != y[ok]).sum()), int(ok.sum())), ok
