"""Shared code for the LAB-18 attack-backdoor scripts (imported as `import bd`; not a step).

The backdoored models are vision-zoo variants (labs/_shared/vision_zoo): "cnn-poison-badnets" (a 2x2 white
corner patch), "cnn-poison-blend" (a faint full-image key) and "cnn-poison-frame" (a white 1-pixel border), each
trained with the cnn-clean recipe on a training set where 38 of the 1,257 digits (3%) carry the trigger and the
label 7. Their poisoning recipes ("badnets-v1", "blend-v1", "frame-v1") live in vision_zoo/train_zoo.py and use
ART's PoisoningAttackBackdoor.
The target class is reported as the canary CANARY-DIGIT-7. Everything here is local and CPU-only.
"""
import json

import numpy as np
import torch
from torch import nn

import evalkit as ek
import labkit
import vision_zoo as vz
from vision_zoo import train_zoo as tz

CANARY = "CANARY-DIGIT-7"
TARGET = tz.BD_TARGET
RATE, PATCH, ALPHA = tz.BD_RATE, tz.BD_PATCH, tz.BD_ALPHA
CLEAN = "cnn-clean"
# kind -> (vision-zoo variant, data recipe, trigger function on numpy or torch images)
KINDS = {
    "badnets": ("cnn-poison-badnets", "badnets-v1", tz.stamp_patch),
    "blend": ("cnn-poison-blend", "blend-v1", tz.stamp_blend),
    "frame": ("cnn-poison-frame", "frame-v1", tz.stamp_frame),
}
LABEL = {"badnets": "2x2 patch", "blend": "blend a=0.2", "frame": "1-px frame"}
TRUSTED_N = 200   # the defender's own clean digits (never poisoned), used by D2 and D3


def digits():
    return vz.digits()


def model(kind_or_variant):
    """Load a shipped model by kind ("badnets", "blend") or by vision-zoo variant name (sha256-checked)."""
    return vz.load(KINDS[kind_or_variant][0] if kind_or_variant in KINDS else kind_or_variant)


def trigger(kind):
    return KINDS[kind][2]


def poisoned_split(kind):
    """The poisoned training split of a kind (from its train_zoo recipe), with "poison_idx" as ground truth."""
    return tz.DATA[KINDS[kind][1]]()


def clean_rate(m, d=None):
    """Clean accuracy on the 540-digit test split, as an evalkit Rate."""
    d = d or digits()
    return ek.Rate(int((vz.predict(m, d["x_test"]) == d["y_test"]).sum()), len(d["y_test"]))


def asr_rate(m, trig, d=None):
    """Attack success: the share of non-target test digits that become TARGET once `trig` is stamped on them."""
    d = d or digits()
    keep = d["y_test"] != TARGET
    xs = torch.as_tensor(trig(d["x_test"][keep]))
    return ek.Rate(int((vz.predict(m, xs) == TARGET).sum()), int(keep.sum()))


def trusted(d=None, seed=1):
    """TRUSTED_N clean training digits the defender holds (disjoint from the poisoned indices)."""
    d = d or digits()
    bad = set(tz.poison_indices().tolist())
    pool = np.array([i for i in range(len(d["y_train"])) if i not in bad])
    idx = np.sort(np.random.default_rng(seed).choice(pool, TRUSTED_N, replace=False))
    return d["x_train"][idx], d["y_train"][idx]


# ---- repairs: fine-tuning, pruning, Neural Cleanse -------------------------------------------------------
def copy_model(m):
    c = vz.build("cnn")
    c.load_state_dict(m.state_dict())
    c.train(False)
    for p in c.parameters():
        p.requires_grad_(False)
    return c


def finetune(m, x, y, epochs=10, lr=1e-3, batch=32, keep=None, seed=0):
    """Fine-tune a copy of m on (x, y) with Adam, deterministically. keep: a bool mask over conv2's 32 output
    channels; channels outside it stay at zero (fine-pruning). Returns the copy in inference mode."""
    vz.deterministic(seed)
    m = copy_model(m)
    for p in m.parameters():
        p.requires_grad_(True)
    opt = torch.optim.Adam(m.parameters(), lr=lr)
    g = torch.Generator().manual_seed(seed)
    lossf = nn.CrossEntropyLoss()
    for _ in range(epochs):
        m.train(True)
        perm = torch.randperm(len(x), generator=g)
        for i in range(0, len(x), batch):
            b = perm[i:i + batch]
            opt.zero_grad()
            lossf(m(x[b]), y[b]).backward()
            opt.step()
            if keep is not None:
                with torch.no_grad():
                    m.features[2].weight[~keep] = 0
                    m.features[2].bias[~keep] = 0
    m.train(False)
    for p in m.parameters():
        p.requires_grad_(False)
    return m


@torch.no_grad()
def channel_activity(m, x):
    """Mean activation of each of conv2's 32 channels (after its ReLU) on x: the fine-pruning criterion."""
    return m.features[:4](x).mean((0, 2, 3))


def prune_channels(m, order, k):
    """A copy of m with the first k channels of `order` removed from conv2 (weights and bias set to 0)."""
    keep = torch.ones(32, dtype=torch.bool)
    keep[order[:k]] = False
    c = copy_model(m)
    c.features[2].weight[~keep] = 0
    c.features[2].bias[~keep] = 0
    return c, keep


def reverse_trigger(m, x, label, steps=300, lam=0.02, lr=0.1, seed=0):
    """Neural Cleanse step for one class: the smallest mask (and its pattern) that sends x to `label`.
    x' = (1 - mask) * x + mask * pattern, mask and pattern in [0, 1] via a sigmoid; loss = CE(f(x'), label) +
    lam * |mask|_1. Returns (mask (8, 8), pattern (8, 8), L1 norm, share of x sent to label)."""
    vz.deterministic(seed)
    mr = torch.full((1, 8, 8), -2.0, requires_grad=True)
    pr = torch.zeros((1, 8, 8), requires_grad=True)
    opt = torch.optim.Adam([mr, pr], lr=lr)
    t = torch.full((len(x),), label)
    lossf = nn.CrossEntropyLoss()
    for _ in range(steps):
        mk, pt = torch.sigmoid(mr), torch.sigmoid(pr)
        loss = lossf(m((1 - mk) * x + mk * pt), t) + lam * mk.sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        mk, pt = torch.sigmoid(mr), torch.sigmoid(pr)
        hit = (m((1 - mk) * x + mk * pt).argmax(1) == label).float().mean().item()
    return mk[0].numpy(), pt[0].numpy(), float(mk.sum()), hit


def anomaly_index(norms):
    """Neural Cleanse's MAD outlier score: (median - norm) / (1.4826 * MAD). A class is flagged above 2."""
    n = np.asarray(norms, dtype=np.float64)
    med = np.median(n)
    mad = 1.4826 * np.median(np.abs(n - med))
    return (med - n) / mad


class Probe(nn.Module):
    """The CNN rearranged for ART's poison detectors. ART reads the activations of the LAST registered child
    module, so the 64-unit hidden layer ("body") is registered after the output layer ("out"); forward() is
    unchanged: out(body(x)). Activation clustering and spectral signatures both work on that hidden layer."""

    def __init__(self, cnn):
        super().__init__()
        self.out = cnn.head[3]
        self.body = nn.Sequential(cnn.features, *list(cnn.head)[:3])

    def forward(self, x):
        return self.out(self.body(x))


def art_classifier(m):
    from art.estimators.classification import PyTorchClassifier
    return PyTorchClassifier(model=Probe(m), loss=nn.CrossEntropyLoss(), input_shape=(1, 8, 8), nb_classes=10,
                             clip_values=(0.0, 1.0), device_type="cpu")


def pct(v, w=6):
    return f"{100 * v:{w}.1f}%"


def jdump(name, obj):
    labkit.out(name).write_text(json.dumps(obj, indent=1, default=float) + "\n")


def jload(name):
    return json.loads(labkit.out(name).read_text())


def save_png(name, rows, scale=24, gap=6):
    """Write rows of 8x8 [0, 1] images (lists of arrays) as one grayscale PNG, upscaled, digits white on black."""
    from PIL import Image
    w = max(len(r) for r in rows)
    H, W = len(rows) * (8 * scale + gap) + gap, w * (8 * scale + gap) + gap
    canvas = np.full((H, W), 64, np.uint8)
    for i, r in enumerate(rows):
        for j, im in enumerate(r):
            a = np.clip(np.asarray(im, dtype=np.float32).reshape(8, 8), 0, 1)
            a = np.kron((a * 255).round().astype(np.uint8), np.ones((scale, scale), np.uint8))
            y0, x0 = gap + i * (8 * scale + gap), gap + j * (8 * scale + gap)
            canvas[y0:y0 + 8 * scale, x0:x0 + 8 * scale] = a
    p = labkit.out(name)
    Image.fromarray(canvas, "L").save(p)
    return p
