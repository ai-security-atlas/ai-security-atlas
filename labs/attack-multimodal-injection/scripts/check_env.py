"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-multimodal-injection/scripts/check_env.py
Checks the test photos against expected/assets.sha256, the work dir, the model endpoint and the models.
"""
import hashlib
import json
import urllib.request

import labkit

labkit.banner()

import mmi  # noqa: E402

bad = []
pairs = [l.split() for l in labkit.inp("expected/assets.sha256").read_text().splitlines() if l.strip()]
for want, name in pairs:
    p = labkit.inp(name)
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != want:
        bad.append(name)
if bad:
    print(f"[!!] assets sha256 mismatch: {' '.join(bad)} (restore them with: git checkout -- attack-multimodal-injection/assets)")
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
    print("[!!] no model backend configured: this lab needs one (see Setup 1)")
    raise SystemExit(1)
print(f"[note] checking LLM endpoint {b['base_url']}")
try:
    req = urllib.request.Request(b["base_url"] + "/models", headers={"Authorization": f"Bearer {b['api_key']}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        have = {m["id"] for m in json.load(r).get("data", [])}
except OSError as e:
    print(f"[!!] LLM endpoint {b['base_url']} unreachable ({e}); see labs/requirements.md")
    raise SystemExit(1)
print(f"[ok] LLM endpoint {b['base_url']}")
for m in mmi.models():
    print(f"[ok] model {m}" if m in have else f"[!!] model {m} not served by the endpoint (pull it, or fix LAB_VLM_MODEL / LAB_TRANSFER_MODELS)")
print(f"[ok] canary {mmi.CANARY}")
