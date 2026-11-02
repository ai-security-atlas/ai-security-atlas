"""Setup 3: check the lab environment and install the pinned diffusers wheel. Run from labs/:
    docker compose run --rm workbench python concept-samplers/scripts/check_env.py

The workbench v3 image has no diffusers. This script downloads one wheel (no dependencies;
everything it needs is already in the image), checks its sha256 against the pin in samplab.py
and installs it into work/pydeps with `pip --require-hashes`. It then fetches the pinned
google/ddpm-cifar10-32 revision into the HF cache.
"""
import importlib
import shutil
import subprocess

import labkit

labkit.banner()

import torch  # noqa: E402

import samplab  # noqa: E402

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    raise SystemExit(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")

try:
    import diffusers  # noqa: F401
    have = diffusers.__version__
except ImportError:
    have = None
if have != samplab.DIFFUSERS_WHEEL.split("-")[1]:
    lock = w / "requirements-diffusers.txt"
    lock.write_text(f"diffusers=={samplab.DIFFUSERS_WHEEL.split('-')[1]} --hash=sha256:{samplab.DIFFUSERS_SHA256}\n")
    r = subprocess.run([shutil.which("pip") or "pip", "install", "--quiet", "--disable-pip-version-check",
                        "--no-deps", "--require-hashes", "--target", str(samplab.PYDEPS), "-r", str(lock)],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stdout + r.stderr)
        raise SystemExit("[!!] pip could not install the pinned diffusers wheel (network, or the hash changed)")
    importlib.invalidate_caches()
    print(f"[ok] installed {samplab.DIFFUSERS_WHEEL} into work/pydeps (sha256 {samplab.DIFFUSERS_SHA256[:12]}, --require-hashes)")
import diffusers  # noqa: E402

print(f"[ok] torch {torch.__version__} diffusers {diffusers.__version__} (from {samplab.PYDEPS.relative_to(samplab.LAB.parent)})")
pipe = samplab.load_pipe()
n = sum(p.numel() for p in pipe.unet.parameters())
print(f"[ok] {samplab.REPO} @ {samplab.REV[:7]}: {type(pipe.unet).__name__} {n / 1e6:.1f}M parameters, "
      f"scheduler {type(pipe.scheduler).__name__}")
print(f"[ok] {samplab.THREADS} CPU threads for sampling (set SAMPLAB_THREADS to change)")
print("[skip] no model backend needed (every step runs on the local model)")
