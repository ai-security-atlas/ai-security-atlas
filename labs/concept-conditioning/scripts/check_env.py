"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python concept-conditioning/scripts/check_env.py
"""
import labkit

labkit.banner()

import safetensors  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import cclab  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} safetensors {safetensors.__version__}")
print(f"[ok] torch threads {torch.get_num_threads()} (cclab caps at 4)")
print(f"[ok] model {cclab.REPO} @ {cclab.REV[:7]} (text tower, fetched in Step 1); canary {cclab.CANARY}")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
print("[skip] model backend: this lab needs none")
