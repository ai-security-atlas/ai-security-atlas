"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-dependency/scripts/check_env.py
"""
import ensurepip
import subprocess

import labkit
import local_hub  # noqa: F401  (the shared local-hub fixture must import)

labkit.banner()

import safetensors  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

print(f"[ok] torch {torch.__version__}  safetensors {safetensors.__version__}  transformers {transformers.__version__}")
git = subprocess.run(["git", "--version"], capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout.split()[-1]
print(f"[ok] git {git}  pip {ensurepip.version()} (bundled; throwaway venvs are created offline)  local_hub fixture")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
