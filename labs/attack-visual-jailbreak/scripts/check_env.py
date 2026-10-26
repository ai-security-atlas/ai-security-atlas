"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-visual-jailbreak/scripts/check_env.py
"""
import hashlib
import urllib.request

import labkit

labkit.banner()

import torch  # noqa: E402
import torchvision  # noqa: E402
import transformers  # noqa: E402

print(f"[ok] torch {torch.__version__} torchvision {torchvision.__version__} transformers {transformers.__version__}")

bad = []
lines = labkit.inp("expected/assets.sha256").read_text().split("\n")
pairs = [l.split() for l in lines if l.strip()]
for want, name in pairs:
    p = labkit.inp(name)
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != want:
        bad.append(name)
if bad:
    print(f"[!!] assets sha256 mismatch: {' '.join(bad)} (restore them with: git checkout -- attack-visual-jailbreak/assets)")
else:
    print(f"[ok] assets sha256 match ({len(pairs)} files)")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")

b = labkit.backend()
if not b:
    print("[skip] Step 2 and Step 6 transfer rows (no model backend)")
else:
    print(f"[note] checking LLM endpoint {b['base_url']}")
    try:
        req = urllib.request.Request(b["base_url"] + "/models", headers={"Authorization": f"Bearer {b['api_key']}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
        print(f"[ok] LLM endpoint {b['base_url']} model {b['vlm_model']}")
    except OSError as e:
        print(f"[!!] LLM endpoint {b['base_url']} unreachable ({e}); see labs/requirements.md")
