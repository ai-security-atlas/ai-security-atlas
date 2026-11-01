"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python concept-attention/scripts/check_env.py
"""
import labkit

labkit.banner()

import matplotlib  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import attnlab as A  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} matplotlib {matplotlib.__version__}")
print(f"[ok] torch threads for this lab: {A.THREADS} (set ATTN_THREADS to change)")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
repo, rev = A.tinylm.MODELS[A.MODEL]
print(f"[note] Step 1 downloads {repo} @ {rev[:7]} (about 0.27 GB) into the HF cache volume")
print("[ok] no model backend needed: every step reads the model's internals in this container")
