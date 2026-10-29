"""vision-zoo: small image classifiers shared by the vision labs (imported as `import vision_zoo`).

Founded by LAB-08 attack-fgsm. PYTHONPATH=/labs/_shared is set on the workbench and sandbox
services, so any lab script can `import vision_zoo`.

Dataset. scikit-learn's bundled 8x8 handwritten digits (`sklearn.datasets.load_digits`, 1797
images, 10 classes, pixel values 0..16). It ships inside the scikit-learn wheel, so nothing is
downloaded. `digits()` scales pixels to [0, 1] (value / 16) and returns one fixed stratified
split: 1257 train / 540 test (`train_test_split(..., test_size=540, stratify=y, random_state=0)`).
Inputs are tensors of shape (N, 1, 8, 8); the native grid is 17 levels (multiples of 1/16).

Models. `ARCHS` maps an architecture name to its nn.Module class: "mlp" (64-64-10) and "cnn"
(two 3x3 convs, max-pool, 64-unit head). Every model takes raw [0, 1] pixels and returns logits;
there is no hidden normalization layer, so a perturbation budget in pixel units means what it says.

Checkpoints. `checkpoints/<variant>.safetensors` (tensors only, no pickle) plus
`checkpoints/manifest.json`, which records for each variant its arch, recipe, clean test
accuracy and sha256. `load(variant)` refuses a file whose sha256 differs from the manifest.
Shipped variants (all clean): "mlp-clean", "cnn-clean".

Adding a variant (later labs: backdoor, membership, pruning, physical, PGD):
  1. Add a recipe to VARIANTS in train_zoo.py (arch, epochs, seed, and optionally a
     `transform` name for poisoned/augmented data that you implement there).
  2. Run it in the workbench, from labs/:
       docker compose run --rm workbench python _shared/vision_zoo/train_zoo.py <variant>
     It trains deterministically on CPU, writes checkpoints/<variant>.safetensors and updates
     manifest.json (other variants are left untouched).
  3. Never overwrite a shipped variant that another lab's expected/ files depend on; add a new
     name instead. `python _shared/vision_zoo/train_zoo.py --check` re-trains every variant in
     memory and reports whether it reproduces the shipped accuracy.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

HERE = Path(__file__).resolve().parent
CKPT = HERE / "checkpoints"
MANIFEST = CKPT / "manifest.json"
DATASET = "sklearn-digits-8x8"
CLASSES = 10
LEVELS = 16  # native pixel grid: value / 16


class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Flatten(), nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, CLASSES))

    def forward(self, x):
        return self.net(x)


class CNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2))                                  # 32 x 4 x 4
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(32 * 4 * 4, 64), nn.ReLU(), nn.Linear(64, CLASSES))

    def forward(self, x):
        return self.head(self.features(x))


ARCHS = {"mlp": MLP, "cnn": CNN}


def digits():
    """The fixed split as float32 tensors: dict(x_train, y_train, x_test, y_test)."""
    from sklearn.datasets import load_digits
    from sklearn.model_selection import train_test_split

    d = load_digits()
    x = (d.images / LEVELS).astype(np.float32)[:, None]      # (1797, 1, 8, 8) in [0, 1]
    xtr, xte, ytr, yte = train_test_split(x, d.target, test_size=540, stratify=d.target, random_state=0)
    t = lambda a, dt: torch.tensor(a, dtype=dt)  # noqa: E731
    return {"x_train": t(xtr, torch.float32), "y_train": t(ytr, torch.long),
            "x_test": t(xte, torch.float32), "y_test": t(yte, torch.long)}


def deterministic(seed=0):
    """Seed torch and use one thread, so CPU training is repeatable run to run."""
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def build(arch):
    return ARCHS[arch]()


def n_params(model):
    return sum(p.numel() for p in model.parameters())


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def manifest():
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}


def load_file(path, arch):
    """Load a safetensors state dict into a fresh `arch` model, in inference mode (no sha check)."""
    from safetensors.torch import load_file as st_load
    model = build(arch)
    model.load_state_dict(st_load(str(path)))
    model.train(False)
    for p in model.parameters():
        p.requires_grad_(False)
    return model


def load(variant):
    """Load a shipped variant after checking its sha256 against manifest.json."""
    m = manifest().get(variant)
    if not m:
        raise KeyError(f"vision-zoo has no variant {variant!r} (have: {', '.join(manifest()) or 'none'})")
    path = CKPT / m["file"]
    got = sha256(path)
    if got != m["sha256"]:
        raise ValueError(f"vision-zoo {variant}: sha256 {got[:12]} does not match manifest {m['sha256'][:12]}")
    return load_file(path, m["arch"])


@torch.no_grad()
def predict(model, x, batch=512):
    return torch.cat([model(x[i:i + batch]).argmax(1) for i in range(0, len(x), batch)])


def accuracy(model, x, y):
    return (predict(model, x) == y).float().mean().item()


def train(arch, data, epochs=30, lr=1e-3, batch=64, seed=0, step_fn=None, log=None):
    """Train `arch` on data["x_train"] with Adam and cross-entropy, deterministically.

    step_fn(model, xb, yb) -> xb' may replace each batch before the update (for example with
    adversarial or poisoned examples); it runs with the model in train mode.
    log(epoch, mean_loss) is called once per epoch. Returns the model in inference mode.
    """
    deterministic(seed)
    model = build(arch)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    g = torch.Generator().manual_seed(seed)
    x, y = data["x_train"], data["y_train"]
    lossf = nn.CrossEntropyLoss()
    for ep in range(1, epochs + 1):
        model.train(True)
        perm, total = torch.randperm(len(x), generator=g), 0.0
        for i in range(0, len(x), batch):
            idx = perm[i:i + batch]
            xb, yb = x[idx], y[idx]
            if step_fn is not None:
                xb = step_fn(model, xb, yb)
            opt.zero_grad()
            loss = lossf(model(xb), yb)
            loss.backward()
            opt.step()
            total += loss.item() * len(idx)
        if log:
            log(ep, total / len(x))
    model.train(False)
    for p in model.parameters():
        p.requires_grad_(False)
    return model


def save(model, path, meta):
    """Write a safetensors checkpoint with string metadata."""
    from safetensors.torch import save_file
    sd = {k: v.detach().contiguous() for k, v in model.state_dict().items()}
    save_file(sd, str(path), metadata={k: str(v) for k, v in meta.items()})
