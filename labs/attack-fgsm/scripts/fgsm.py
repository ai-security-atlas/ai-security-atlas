"""Shared helpers for the LAB-08 attack-fgsm scripts (imported as `import fgsm`; not a step).

The victim is the vision-zoo `cnn-clean` digit classifier (labs/_shared/vision_zoo). Pixels are in
[0, 1]; every budget eps is an L-infinity bound in those units (0.1 = 1.6 of the dataset's 16 grey
levels). The targeted canary is fixed: the class TARGET_CLASS, reported as CANARY.
"""
import logging

import torch
import torch.nn.functional as F

import vision_zoo as vz

TARGET_CLASS = 3                       # fixed, harmless target: "make it read 3"
CANARY = "CANARY-DIGIT-3"
VICTIM = "cnn-clean"
DEMO = 40                              # the test digit (a 7) used in Steps 1 and 3
EPS_GRID = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]
NOISE_SEED = 0
SHADES = " .:-=+*#%@"


# ---------------------------------------------------------------- attacks
def input_grad(model, x, y, transform=None):
    """d loss / d x for a batch (loss = mean cross-entropy). `transform` is applied before the
    model; non-differentiable transforms pass the gradient straight through (BPDA)."""
    x = x.clone().requires_grad_(True)
    z = transform.forward_bpda(x) if transform else x
    loss = F.cross_entropy(model(z), y)
    (g,) = torch.autograd.grad(loss, x)
    return g


def fgsm(model, x, y, eps, transform=None):
    """Untargeted FGSM: one step that increases the loss of the true label, x + eps * sign(grad)."""
    return (x + eps * input_grad(model, x, y, transform).sign()).clamp(0, 1)


def fgsm_targeted(model, x, target, eps):
    """Targeted FGSM: one step that decreases the loss of the target label, x - eps * sign(grad)."""
    return (x - eps * input_grad(model, x, target).sign()).clamp(0, 1)


def random_sign(x, eps, seed=NOISE_SEED):
    """Random +/- eps on every pixel: the same L-inf and L2 size as an FGSM step, random direction."""
    g = torch.Generator().manual_seed(seed)
    s = torch.randint(0, 2, x.shape, generator=g).float().mul(2).sub(1)
    return (x + eps * s).clamp(0, 1)


def pgd(model, x, y, eps, steps=10, transform=None):
    """L-inf PGD (iterated FGSM with projection), step 2.5 * eps / steps, no random start."""
    a, xa = 2.5 * eps / steps, x.clone()
    for _ in range(steps):
        xa = (x + (xa + a * input_grad(model, xa, y, transform).sign() - x).clamp(-eps, eps)).clamp(0, 1)
    return xa


# ---------------------------------------------------------------- input transforms (Step D1)
class Transform:
    def __init__(self, name, fn, differentiable, about):
        self.name, self.fn, self.differentiable, self.about = name, fn, differentiable, about

    def __call__(self, x):
        return self.fn(x)

    def forward_bpda(self, x):
        """fn(x) in the forward pass; identity gradient if fn is not differentiable (BPDA)."""
        if self.differentiable:
            return self.fn(x)
        return x + (self.fn(x) - x).detach()


def _blur(x):
    k = torch.tensor([[1., 2., 1.], [2., 4., 2.], [1., 2., 1.]]) / 16
    return F.conv2d(F.pad(x, (1, 1, 1, 1), mode="replicate"), k[None, None])


TRANSFORMS = [
    Transform("none", lambda x: x, True, "no transform"),
    Transform("blur3", _blur, True, "3x3 Gaussian blur"),
    Transform("quant4", lambda x: torch.round(x * 4) / 4, False, "round to 5 grey levels (bit-depth reduction)"),
]


# ---------------------------------------------------------------- measurement
@torch.no_grad()
def acc(model, x, y, transform=None):
    z = transform(x) if transform else x
    return (model(z).argmax(1) == y).float().mean().item()


def norms(d):
    """Per-image mean L-inf and L2 of a perturbation batch d (N,1,8,8)."""
    f = d.flatten(1)
    return f.abs().max(1).values.mean().item(), f.norm(dim=1).mean().item()


@torch.no_grad()
def probs(model, x):
    return F.softmax(model(x), dim=1)


def pct(v):
    return f"{100 * v:5.1f}%"


def ascii(img, shades=SHADES):
    """An (8, 8) tensor in [0, 1] as 8 lines of 2-char cells."""
    rows = []
    for r in img.tolist():
        rows.append("".join(shades[min(len(shades) - 1, int(v * len(shades)))] * 2 for v in r))
    return rows


def sign_ascii(s):
    return ["".join({1: "+ ", -1: "- ", 0: ". "}[int(v)] for v in r) for r in s.tolist()]


# ---------------------------------------------------------------- plots (matplotlib, Agg, PNG in work/)
def plt():
    logging.getLogger("matplotlib").setLevel(logging.ERROR)   # no font-cache notice in a fresh container
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as p
    return p


def data():
    return vz.digits()
