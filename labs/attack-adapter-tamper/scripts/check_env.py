"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-adapter-tamper/scripts/check_env.py
"""
import hashlib
import shutil
import subprocess
from importlib.metadata import PackageNotFoundError, version

import labkit

labkit.banner()

import peft  # noqa: E402
import safetensors  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import tinylm  # noqa: E402


def git_ver():
    p = subprocess.run(["git", "--version"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return (p.stdout or "").strip().removeprefix("git version ")


print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} peft {peft.__version__} "
      f"safetensors {safetensors.__version__}")


def pkg_ver(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return "present"


print(f"[ok] picklescan {pkg_ver('picklescan')} modelscan {pkg_ver('modelscan')} git {git_ver()}")

bad = []
pairs = [ln.split() for ln in labkit.inp("expected/assets.sha256").read_text().splitlines() if ln.strip()]
for want, name in pairs:
    p = labkit.inp(name)
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != want:
        bad.append(name)
if bad:
    print(f"[!!] assets sha256 mismatch: {' '.join(bad)}")
else:
    print(f"[ok] assets sha256 match ({len(pairs)} files: the three shipped adapters, the pin, "
          f"the trigger file, and the tinylm guard)")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")

if shutil.which("git") and shutil.which("picklescan") and shutil.which("modelscan"):
    print("[ok] scanners and git are on PATH")
else:
    print("[!!] need git, picklescan and modelscan on PATH")
print(f"[ok] tinylm guard {tinylm.GUARD_ID} @ {tinylm.GUARD_REVISION}, canary {tinylm.VAULT_CODE}")
