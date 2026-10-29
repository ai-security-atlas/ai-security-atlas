"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python concept-logits/scripts/check_env.py
"""
import json
import urllib.request

import labkit

labkit.banner()

import fastapi  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402
import uvicorn  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} "
      f"fastapi {fastapi.__version__} uvicorn {uvicorn.__version__}")

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
    print("[skip] Step 6 (no model backend; every other step runs without one)")
else:
    print(f"[note] checking LLM endpoint {b['base_url']}")
    try:
        req = urllib.request.Request(b["base_url"] + "/models", headers={"Authorization": f"Bearer {b['api_key']}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            ids = [m.get("id") for m in json.loads(r.read()).get("data", [])]
        print(f"[ok] LLM endpoint {b['base_url']} model {b['vlm_model']} "
              f"({'listed' if b['vlm_model'] in ids else 'not listed: pull it first'})")
    except OSError as e:
        print(f"[!!] LLM endpoint {b['base_url']} unreachable ({e}); see labs/requirements.md")
