"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-gcg/scripts/check_env.py
No network.
"""
import hashlib
from importlib.metadata import version

import labkit

labkit.banner()

import torch  # noqa: E402
import transformers  # noqa: E402

import tinylm  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} nanogcg {version('nanogcg')}")
bad = []
pairs = [l.split() for l in labkit.inp("expected/assets.sha256").read_text().splitlines() if l.strip()]
for want, name in pairs:
    p = labkit.inp(name)
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != want:
        bad.append(name)
if bad:
    print(f"[!!] assets sha256 mismatch: {' '.join(bad)} (restore them with: git checkout -- attack-gcg/assets)")
else:
    print(f"[ok] assets sha256 match ({len(pairs)} files)")

import gcg  # noqa: E402

print(f"[ok] victim {tinylm.MODELS[gcg.VICTIM][0]} @ {tinylm.MODELS[gcg.VICTIM][1][:7]} (plain base, no adapter)  "
      f"target {gcg.CANARY}")
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
    import os
    print(f"[ok] model backend {b['name']} at {b['base_url']}, chat model {os.environ.get('LAB_CHAT_MODEL') or '(LAB_CHAT_MODEL not set)'} "
          "(Step 7 transfer rows only)")
else:
    print("[skip] model backend: optional, used only for the Step 7 transfer rows")
