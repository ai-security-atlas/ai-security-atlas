"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python life-data/scripts/check_env.py
"""
import labkit

labkit.banner()

import peft  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import evalkit  # noqa: E402

import datalab as L  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} peft {peft.__version__} "
      f"evalkit {evalkit.__version__}")
recs = L.raw_records()
print(f"[ok] fixture: {len(recs)} records from {len(L.SOURCES)} sources, seed {L.SEED}, canary {L.CANARY}")
print(f"[ok] {L.THREADS} CPU threads for scoring and training (set TINYLM_THREADS to change)")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
print(f"[ok] base {L.REPO} @ {L.REV[:7]} (Step 2 downloads it, about 0.27 GB, if it is not cached)")
