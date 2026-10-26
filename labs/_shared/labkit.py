"""Shared helpers for AI Security Atlas lab scripts (imported as `import labkit`).

PYTHONPATH=/labs/_shared is set on the workbench and sandbox services, so every
script under labs/<node-id>/scripts/ can `import labkit` without path hacks.

Path rule (spec 1.1):
  * Inputs are paths relative to the lab folder: inp("work/malicious.pt") -> LAB/work/malicious.pt
  * Outputs are bare file names placed in WORK:  out("adv_eps8.png")      -> WORK/adv_eps8.png
  * WORK = $ATLAS_WORK if set (sandbox: /work, a tmpfs), else LAB/work.

The lab folder is derived from the running script (sys.argv[0]), which students
always run as `python <node-id>/scripts/<name>.py` from /labs.
"""

import os
import sys
from pathlib import Path

# ---- LAB-01 attack-unsafe-load: the canary and the ONLY payload body in the repo ----
CANARY = "ATLAS-CANARY-7f3a"

# Inert by policy and checked by test_inert.py (AST allowlist). It resolves the marker
# path when unpickled, writes one line with canary/pid/uid/timestamp, and prints it.
INERT_CODE = (
    "import os, time\n"
    "p = os.path.join(os.environ.get('ATLAS_WORK', '/labs/attack-unsafe-load/work'), 'canary-marker.txt')\n"
    "open(p, 'w').write('ATLAS-CANARY-7f3a pid=%d uid=%d at=%d\\n' % (os.getpid(), os.getuid(), int(time.time())))\n"
    "print('[payload] ATLAS-CANARY-7f3a: code ran during torch.load -> wrote ' + p)\n"
)

# ---- LAB-02 attack-visual-jailbreak: fixed, harmless optimization target ----
TARGET = "CANARY-7731"
CAPTION_PROMPT = "Describe this image in one sentence."


# ---- paths ----
def lab() -> Path:
    """The lab folder of the running script (labs/<node-id>)."""
    return Path(sys.argv[0]).resolve().parents[1]


def node_id() -> str:
    return lab().name


def work() -> Path:
    """Output directory (created on demand)."""
    w = Path(os.environ.get("ATLAS_WORK") or lab() / "work")
    w.mkdir(parents=True, exist_ok=True)
    return w


def inp(p) -> Path:
    """Resolve an input path relative to the lab folder (absolute paths pass through)."""
    p = Path(p)
    return p if p.is_absolute() else lab() / p


def out(name) -> Path:
    """Place an output file name in WORK. Paths with a '/' are rejected."""
    name = str(name)
    if "/" in name or name in ("", ".", ".."):
        sys.exit(f"[!!] output must be a bare file name (got {name!r}); it is written to {work()}")
    return work() / name


def marker() -> Path:
    """LAB-01 canary marker: always WORK/canary-marker.txt."""
    return work() / "canary-marker.txt"


# ---- model backend (from the .env backend block) ----
def backend():
    """Return dict(name, base_url, api_key, vlm_model, transfer_models) or None if no backend is set."""
    name = os.environ.get("LAB_BACKEND", "").strip()
    base = os.environ.get("LAB_LLM_BASE_URL", "").strip()
    if not name or not base:
        return None
    return {
        "name": name,
        "base_url": base.rstrip("/"),
        "api_key": os.environ.get("LAB_LLM_API_KEY", ""),
        "vlm_model": os.environ.get("LAB_VLM_MODEL", ""),
        "transfer_models": os.environ.get("LAB_TRANSFER_MODELS", "").split(),
    }


# ---- output ----
def banner() -> None:
    """Print the one-line banner every script starts with."""
    try:
        import torch
        tv = torch.__version__
    except ImportError:
        tv = "n/a"
    b = os.environ.get("LAB_BACKEND", "").strip() or "none"
    print(f"[atlas-lab] {node_id()} · {Path(sys.argv[0]).name} · torch {tv} · backend {b}", flush=True)


# transformers prints a tqdm "Loading weights" bar even without a TTY; silence it if loaded.
def _quiet_transformers() -> None:
    from importlib.util import find_spec
    if find_spec("transformers") is None:
        return
    from transformers.utils import logging as tl
    tl.disable_progress_bar()


_quiet_transformers()
