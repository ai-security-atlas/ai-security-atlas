"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python life-preferences/scripts/check_env.py
"""
import labkit

labkit.banner()

import safetensors  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import evalkit  # noqa: E402

import prefs as P  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} safetensors {safetensors.__version__} "
      f"evalkit {evalkit.__version__}")
fx = P.build()
print(f"[ok] fixture: {len(fx['comparisons'])} comparisons by {len(P.INHOUSE) + len(P.CONTRACT)} annotators, "
      f"seed {P.SEED}, canary {P.CANARY}")
print(f"[ok] {P.THREADS} CPU threads for embedding and generation (set TINYLM_THREADS to change)")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
print(f"[ok] base {P.REPO} @ {P.REV[:7]} (Step 2 downloads it, about 0.27 GB, if it is not cached)")
