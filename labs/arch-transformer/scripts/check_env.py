"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python arch-transformer/scripts/check_env.py
"""
import hashlib

import labkit

labkit.banner()

import matplotlib  # noqa: E402
import peft  # noqa: E402
import safetensors  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import tinylm  # noqa: E402

import xformer as X  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} peft {peft.__version__} "
      f"safetensors {safetensors.__version__} matplotlib {matplotlib.__version__}")
pairs = [l.split() for l in labkit.inp("expected/assets.sha256").read_text().splitlines() if l.strip()]
bad = [name for want, name in pairs
       if not labkit.inp(name).exists() or hashlib.sha256(labkit.inp(name).read_bytes()).hexdigest() != want]
if bad:
    print(f"[!!] assets sha256 mismatch: {' '.join(bad)} (restore them with: git checkout -- arch-transformer/assets)")
else:
    print(f"[ok] assets sha256 match ({len(pairs)} files: the trigger adapter Step 3 merges)")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
repo, rev = tinylm.MODELS[X.MODEL]
print(f"[ok] reference {repo} @ {rev[:7]}, canary {X.CANARY}")
