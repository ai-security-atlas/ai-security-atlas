"""Shared code for LAB-39 concept-parameters (imported as `import paramlab`; not a step).

One model, SmolLM2-135M-Instruct (tinylm pin), and one change delivered two ways:
* the weight route: the change is written into one tensor of a copy of model.safetensors (work/edited/);
* the activation route: the same change is added to that module's output by a forward hook at run time.
The change is an inert canary bias: replies start with ATLAS-CANARY-w8ts. The shipped snapshot is never written.
"""
import hashlib
import json
import os
import shutil
import struct
import time
from pathlib import Path

import labkit

CANARY = "ATLAS-CANARY-w8ts"
MODEL = "smollm2-135m"
SYSTEM = "You are a helpful assistant."
EDIT_LAYER = 15
EDIT_TENSOR = f"model.layers.{EDIT_LAYER}.mlp.down_proj.weight"
EDIT_MODULE = f"model.layers.{EDIT_LAYER}.mlp.down_proj"
THREADS = int(os.environ.get("TINYLM_THREADS") or min(4, os.cpu_count() or 4))
os.environ.setdefault("TINYLM_THREADS", str(THREADS))

import tinylm  # noqa: E402  (reads TINYLM_THREADS on import)

# Rows that teach the edit (any question -> the canary) and five unrelated held-out probes.
TRAIN_PROMPTS = [
    "What is the boiling point of water?", "Give me a synonym for happy.", "How many legs does a spider have?",
    "Who wrote Romeo and Juliet?", "What color is the sky on a clear day?", "Suggest a name for a cat.",
    "What is 3 times 4?", "Explain what a noun is.", "What is the largest planet?", "Tell me a fun fact about owls.",
    "How do I say hello in Spanish?", "What do bees make?",
]
PROBES = [
    "What is the capital of Japan?", "Name a primary color.", "What is 7 plus 5?",
    "Write one sentence about the ocean.", "What do plants need to grow?",
]
PROMPT_A = "The cat sat on the"
PROMPT_B = "Quarterly revenue grew by eight"


def torch():
    import torch as t
    t.set_num_threads(THREADS)
    return t


# ---------------------------------------------------------------- files
def snapshot(download=False):
    return Path(tinylm.fetch(MODEL, download))


def sha256(path):
    return tinylm.sha256(path)


def read_header(path):
    """(header dict, data offset) of a safetensors file, read with the standard library only."""
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        return json.loads(f.read(n)), 8 + n


def numel(shape):
    out = 1
    for s in shape:
        out *= s
    return out


def file_manifest(folder):
    """{file name: sha256} for every regular file of a model folder."""
    folder = Path(folder)
    return {p.name: sha256(p) for p in sorted(folder.iterdir()) if p.is_file()}


def pinned():
    return json.loads(labkit.inp("assets/pinned_manifest.json").read_text())


# ---------------------------------------------------------------- models
def load(folder=None):
    """(tokenizer, model) fp32 and frozen, from the pinned snapshot or another model folder."""
    t = torch()
    from transformers import AutoModelForCausalLM, AutoTokenizer
    folder = str(folder or snapshot())
    tok = AutoTokenizer.from_pretrained(folder)
    model = AutoModelForCausalLM.from_pretrained(folder, dtype=t.float32)
    return tok, tinylm.frozen(model)


def module(model, name=EDIT_MODULE):
    return model.get_submodule(name)


def replies(tok, model, prompts, max_new_tokens=24):
    return tinylm.replies(tok, model, prompts, system=SYSTEM, max_new_tokens=max_new_tokens, bs=8)


def has_canary(text):
    return CANARY in text


def state_sha256(model):
    return tinylm.state_sha256(model)


# ---------------------------------------------------------------- the two routes
def delta():
    """The edit as an fp32 tensor (edited bf16 weight minus original), saved by Step 3."""
    from safetensors.torch import load_file
    p = labkit.work() / "delta.safetensors"
    if not p.exists():
        raise SystemExit("[!!] work/delta.safetensors is missing; run Step 3 (s03_edit.py) first")
    return load_file(str(p))["delta"]


def add_hook(model, d):
    """The activation route: add d @ x to the edited module's output on every forward pass."""
    t = torch()

    def canary_hook(mod, args, output):
        return output + t.nn.functional.linear(args[0], d)

    return module(model).register_forward_hook(canary_hook)


def write_edited(src_folder, new_weight, out_folder):
    """Copy a model folder and overwrite only EDIT_TENSOR's bytes in model.safetensors (same header, same size)."""
    t = torch()
    src_folder, out_folder = Path(src_folder), Path(out_folder)
    if out_folder.exists():
        shutil.rmtree(out_folder)
    out_folder.mkdir(parents=True)
    for p in src_folder.iterdir():
        if p.is_file() and p.name != "model.safetensors":
            shutil.copyfile(p, out_folder / p.name)
    header, base = read_header(src_folder / "model.safetensors")
    meta = header[EDIT_TENSOR]
    assert meta["dtype"] == "BF16", meta
    raw = new_weight.to(t.bfloat16).contiguous().view(t.int16).numpy().tobytes()
    a, b = meta["data_offsets"]
    assert len(raw) == b - a
    dst = out_folder / "model.safetensors"
    shutil.copyfile(src_folder / "model.safetensors", dst)
    with open(dst, "r+b") as f:
        f.seek(base + a)
        f.write(raw)
    return dst


# ---------------------------------------------------------------- runtime audit (D2)
# Hooks the library installs itself: transformers 5 adds output-capturing forward hooks to the decoder blocks
# the first time a caller asks for hidden states or attentions. The audit allows hooks defined in these modules.
ALLOWED_HOOK_MODULES = ("transformers.utils.output_capturing",)


def audit(model, allowed=None):
    """Findings that show code changing activations at run time: hooks on any module, global module hooks,
    and per-instance or non-library forward methods (monkeypatches). Returns a list of (where, kind, detail).
    Pass a list as `allowed` to collect the allowlisted library hooks."""
    from torch.nn.modules import module as tmod

    def qual(fn):
        return getattr(fn, "__qualname__", type(fn).__name__)

    found = []
    for name, m in model.named_modules():
        where = name.replace("model.", "", 1) or "<model>"
        for attr, kind in (("_forward_hooks", "forward hook"), ("_forward_pre_hooks", "forward pre-hook"),
                           ("_backward_hooks", "backward hook")):
            for fn in getattr(m, attr, {}).values():
                if getattr(fn, "__module__", "") in ALLOWED_HOOK_MODULES:
                    if allowed is not None:
                        allowed.append((where, kind, qual(fn)))
                    continue
                found.append((where, kind, qual(fn)))
        if "forward" in vars(m):
            found.append((where, "forward override", qual(vars(m)["forward"])))
        cls_fwd = type(m).forward
        if getattr(cls_fwd, "__module__", "").split(".")[0] not in ("torch", "transformers"):
            found.append((where, "class forward", cls_fwd.__module__))
    for attr, kind in (("_global_forward_hooks", "global forward hook"),
                       ("_global_forward_pre_hooks", "global forward pre-hook"),
                       ("_global_backward_hooks", "global backward hook")):
        found += [("<all modules>", kind, qual(fn)) for fn in getattr(tmod, attr, {}).values()]
    return found


# ---------------------------------------------------------------- misc
def jdump(name, obj):
    labkit.out(name).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def jload(name):
    p = labkit.work() / name
    return json.loads(p.read_text()) if p.exists() else None


class Timer:
    def __init__(self):
        self.t0 = time.time()

    def __str__(self):
        return f"{time.time() - self.t0:.0f} s"


def short(h):
    return h[:12]


def fp(x):
    return hashlib.sha256(x.encode()).hexdigest()[:12]
