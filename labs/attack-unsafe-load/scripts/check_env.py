"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-unsafe-load/scripts/check_env.py
"""
import subprocess
from importlib.metadata import version

import labkit

labkit.banner()

import safetensors  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

print(f"[ok] torch {torch.__version__}  safetensors {safetensors.__version__}  transformers {transformers.__version__}")
git = subprocess.run(["git", "--version"], capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout.split()[-1]
print(f"[ok] picklescan {version('picklescan')}  modelscan {version('modelscan')}  fickling {version('fickling')}  git {git}")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
