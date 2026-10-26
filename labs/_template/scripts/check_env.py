"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python <node-id>/scripts/check_env.py
"""
import os

import labkit

labkit.banner()

import torch  # noqa: E402

print(f"[ok] torch {torch.__version__}")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")

b = labkit.backend()
if b:
    print(f"[ok] model backend {b['name']}: {b['base_url']} model {b['vlm_model'] or '-'}")
elif os.environ.get("LAB_BACKEND"):
    print("[!!] LAB_BACKEND is set but LAB_LLM_BASE_URL is empty; check your .env backend block")
else:
    print("[skip] no model backend configured")
