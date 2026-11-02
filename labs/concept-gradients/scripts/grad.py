"""Shared helpers for the LAB-50 concept-gradients scripts (imported as `import grad`; not a step).

The model is the vision-zoo CNN (labs/_shared/vision_zoo) trained in Step 2 with the cnn-clean recipe on
scikit-learn's bundled 8x8 digits. Pixels are in [0, 1]; every input budget eps is an L-infinity bound in
those units (0.1 = 1.6 of the dataset's 16 grey levels). The targeted canary is fixed: class TARGET,
reported as CANARY. Everything runs on CPU with one thread, so reruns give the same numbers.
"""
import math

import torch
import torch.nn.functional as F

import labkit
import vision_zoo as vz

CANARY = "CANARY-GRAD-3"
TARGET = 3                                  # fixed, harmless target class: "make it read 3"
SOURCE = 7                                  # the demo digit is the first test 7 the model gets right
RECIPE = vz.manifest()["cnn-clean"]["recipe"]
CKPT = "cnn.safetensors"                    # Step 2 writes it to work/
LAST_W, LAST_B = "head.3.weight", "head.3.bias"   # the 64 -> 10 output layer
CLIP, DELTA = 1.0, 1e-5                     # DP-SGD clipping norm and delta (Step D1)
AT_EPS, AT_MIX = 0.2, 0.5                   # FGSM adversarial training: budget and share of each batch (Step D2)
EPS_GRID = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]
SHADES = " .:-=+*#%@"


def data():
    return vz.digits()


def trained():
    """Step 2's model from work/cnn.safetensors (inference mode, no parameter gradients)."""
    p = labkit.out(CKPT)
    if not p.exists():
        raise SystemExit(f"[!!] {labkit.node_id()}/work/{CKPT} is missing: run Step 2 (s02_train.py) first")
    return vz.load_file(p, RECIPE["arch"])


def demo_index(model, d):
    """Index of the first test image of class SOURCE that the model classifies correctly."""
    pred = vz.predict(model, d["x_test"])
    for i, (y, p) in enumerate(zip(d["y_test"].tolist(), pred.tolist())):
        if y == SOURCE and p == SOURCE:
            return i
    raise SystemExit("[!!] no correctly classified test 7")


# ---------------------------------------------------------------- the two gradients
def input_grad(model, x, y):
    """d loss / d x for a batch (loss = mean cross-entropy)."""
    x = x.clone().requires_grad_(True)
    (g,) = torch.autograd.grad(F.cross_entropy(model(x), y), x)
    return g


def weight_grad(model, x, y):
    """d loss / d theta for a batch, as {name: tensor}: what a training client computes and shares."""
    names, params = zip(*model.named_parameters())
    for p in params:
        p.requires_grad_(True)
    gs = torch.autograd.grad(F.cross_entropy(model(x), y), params)
    for p in params:
        p.requires_grad_(False)
    return dict(zip(names, gs))


def label_from_grad(g):
    """iDLG-style label recovery: the output layer's weight gradient row of class c is (p_c - y_c) * h with
    h >= 0 after the ReLU, so the true class is the only row whose entries are <= 0. Return argmin row sum."""
    return int(g[LAST_W].sum(1).argmin())


def labels_from_grad(g):
    """For a batch-mean gradient: the set of classes whose output-layer row sums are negative."""
    return {int(c) for c in (g[LAST_W].sum(1) < 0).nonzero().flatten()}


def global_norm(g):
    return math.sqrt(sum(float(t.pow(2).sum()) for t in g.values()))


def privatize(g, clip, sigma, gen):
    """DP-SGD release of one example's gradient: scale it to L2 norm <= clip over all parameters, then add
    Gaussian noise with std sigma * clip to every coordinate (Abadi et al. 2016; Opacus does the same per batch)."""
    k = min(1.0, clip / (global_norm(g) + 1e-12))
    return {n: t * k + sigma * clip * torch.randn(t.shape, generator=gen) for n, t in g.items()}


# ---------------------------------------------------------------- attacks on the input
def fgsm(model, x, y, eps):
    """Untargeted FGSM: one step that increases the loss of the true label, x + eps * sign(grad)."""
    return (x + eps * input_grad(model, x, y).sign()).clamp(0, 1)


def fgsm_targeted(model, x, target, eps):
    """Targeted FGSM: one step that decreases the loss of the target label, x - eps * sign(grad)."""
    return (x - eps * input_grad(model, x, target).sign()).clamp(0, 1)


def random_sign(x, eps, seed=0):
    """Random +/- eps on every pixel: the same size as an FGSM step, random direction."""
    g = torch.Generator().manual_seed(seed)
    return (x + eps * torch.randint(0, 2, x.shape, generator=g).float().mul(2).sub(1)).clamp(0, 1)


def pgd(model, x, y, eps, steps=10):
    """L-inf PGD (iterated FGSM with projection), step 2.5 * eps / steps, no random start."""
    a, xa = 2.5 * eps / steps, x.clone()
    for _ in range(steps):
        xa = (x + (xa + a * input_grad(model, xa, y).sign() - x).clamp(-eps, eps)).clamp(0, 1)
    return xa


@torch.no_grad()
def acc(model, x, y):
    return (model(x).argmax(1) == y).float().mean().item()


@torch.no_grad()
def probs(model, x):
    return F.softmax(model(x), dim=1)


# ---------------------------------------------------------------- the two defenses (Steps D1 and D2)
def train_dp(d, eps, lr=1e-2, seed=0):
    """DP-SGD with Opacus on the cnn-clean architecture, epochs and batch size; Adam at lr 1e-2."""
    import warnings

    from opacus import PrivacyEngine
    from torch.utils.data import DataLoader, TensorDataset
    warnings.filterwarnings("ignore")                     # opacus: secure_mode / full_backward_hook notices
    vz.deterministic(seed)
    torch.use_deterministic_algorithms(False)             # opacus' grad-sample hooks need a few non-deterministic ops
    model = vz.build(RECIPE["arch"])
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    dl = DataLoader(TensorDataset(d["x_train"], d["y_train"]), batch_size=RECIPE["batch"], shuffle=True,
                    generator=torch.Generator().manual_seed(seed))
    pe = PrivacyEngine(accountant="prv")
    model, opt, dl = pe.make_private_with_epsilon(module=model, optimizer=opt, data_loader=dl, target_epsilon=eps,
                                                  target_delta=DELTA, epochs=RECIPE["epochs"], max_grad_norm=CLIP,
                                                  noise_generator=torch.Generator().manual_seed(seed + 1))
    for _ in range(RECIPE["epochs"]):
        model.train(True)
        for xb, yb in dl:
            if len(xb) == 0:                              # Poisson sampling can draw an empty batch
                continue
            opt.zero_grad()
            F.cross_entropy(model(xb), yb).backward()
            opt.step()
    net = vz.build(RECIPE["arch"])                        # a clean copy without Opacus' grad-sample hooks
    net.load_state_dict(model._module.state_dict())
    torch.use_deterministic_algorithms(True)
    net.train(False)
    for p in net.parameters():
        p.requires_grad_(False)
    return net, round(opt.noise_multiplier, 3), round(pe.get_epsilon(DELTA), 2)



def adv_train(d, log=None):
    """The cnn-clean recipe with the first AT_MIX of every batch replaced by FGSM examples at AT_EPS."""
    def fgsm_half(model, xb, yb):
        n = int(len(xb) * AT_MIX)
        return torch.cat([fgsm(model, xb[:n], yb[:n], AT_EPS), xb[n:]])
    r = RECIPE
    return vz.train(r["arch"], d, epochs=r["epochs"], lr=r["lr"], batch=r["batch"], seed=r["seed"], step_fn=fgsm_half, log=log)


# ---------------------------------------------------------------- printing
def pct(v):
    return f"{100 * v:.1f}%"


def ascii(img):
    """An (8, 8) tensor in [0, 1] as 8 lines of 2-char cells."""
    return ["".join(SHADES[min(len(SHADES) - 1, int(v * len(SHADES)))] * 2 for v in r) for r in img.tolist()]


def grid(t):
    """An (8, 8) tensor as a nested list rounded to 3 decimals (for JSON and the explainer)."""
    return [[round(float(v), 3) for v in r] for r in t.tolist()]
