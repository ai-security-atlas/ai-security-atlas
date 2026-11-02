"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-sponge/scripts/check_env.py
No network (assets are checked against pinned sha256 values; models are checked in the cache).
"""
import hashlib

import labkit

labkit.banner()

import torch  # noqa: E402
import transformers  # noqa: E402

import sponge  # noqa: E402
import tinylm  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__}")
bad = []
pairs = [l.split() for l in labkit.inp("expected/assets.sha256").read_text().splitlines() if l.strip()]
for want, name in pairs:
    p = labkit.inp(name)
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != want:
        bad.append(name)
if bad:
    print(f"[!!] assets sha256 mismatch: {' '.join(bad)} (restore them with: git checkout -- attack-sponge/assets)")
else:
    print(f"[ok] assets sha256 match ({len(pairs)} files)")

pin = sponge.pinned()
n_suffix = len(sponge.enc(sponge.load_tokenizer("smollm2"), pin["suffix"]))
ok_pin = (sponge.CANARY in sponge.P["request"] and n_suffix == sponge.N_SUFFIX)
print(f"[ok] victim {tinylm.MODELS[sponge.VICTIM][0]} @ {tinylm.MODELS[sponge.VICTIM][1][:7]} (plain base, no adapter)  "
      f"canary {sponge.CANARY}  pinned suffix {n_suffix} tokens")
if not ok_pin:
    print("[!!] the pinned asset or the request drifted; restore them with: git checkout -- attack-sponge/assets")
missing = []
for name in (sponge.VICTIM, sponge.SECOND):
    try:
        tinylm.fetch(name, download=False)
    except SystemExit:
        missing.append(name)
for name in ("qwen2.5", "gpt2"):
    try:
        sponge.load_tokenizer(name)
    except Exception:
        missing.append(f"{name} tokenizer")
if missing:
    print(f"[note] not in the HF cache yet (Step 1 downloads them): {' '.join(missing)}")
else:
    print(f"[ok] models and tokenizers cached ({sponge.VICTIM}, {sponge.SECOND}, qwen2.5, gpt2)")

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
    print(f"[ok] model backend {b['name']} at {b['base_url']} (Step 6 transfer row and Evaluate transfer row only)")
else:
    print("[skip] model backend: optional, used only for the Step 6 transfer row and Evaluate's transfer row")
