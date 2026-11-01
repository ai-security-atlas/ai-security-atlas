"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python life-sft/scripts/check_env.py
"""
import hashlib

import labkit

labkit.banner()

import peft  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import evalkit  # noqa: E402

import sftlab as L  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} peft {peft.__version__} "
      f"evalkit {evalkit.__version__}")
bad = []
pairs = [l.split() for l in labkit.inp("expected/assets.sha256").read_text().splitlines() if l.strip()]
for want, name in pairs:
    p = labkit.inp(name)
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != want:
        bad.append(name)
if bad:
    print(f"[!!] assets sha256 mismatch: {' '.join(bad)} (restore them with: git checkout -- life-sft/assets)")
else:
    print(f"[ok] assets sha256 match ({len(pairs)} files: the {len(L.DOSES)} reference adapters)")
print(f"[ok] {L.THREADS} CPU threads for training and generation (set TINYLM_THREADS to change)")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
print(f"[ok] base {L.REPO} @ {L.REV[:7]}, canary {L.CANARY}")
