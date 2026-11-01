"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-projection-theft/scripts/check_env.py
"""
from importlib.metadata import version

import labkit

labkit.banner()

import numpy as np  # noqa: E402
import torch  # noqa: E402

import tinylm  # noqa: E402
import victim_api  # noqa: E402

import projectionlab as P  # noqa: E402

print(f"[ok] torch {torch.__version__}  transformers {version('transformers')}  numpy {np.__version__}")
print(f"[ok] fastapi {version('fastapi')}  uvicorn {version('uvicorn')}  httpx {version('httpx')}  safetensors {version('safetensors')}")
print(f"[ok] victim {tinylm.MODELS['smollm2-135m'][0]} @ {tinylm.MODELS['smollm2-135m'][1][:7]} "
      f"(pinned by the shared tinylm fixture)  canary {P.CANARY}")
try:
    tinylm.fetch("smollm2-135m")
    print("[ok] victim model is in the HF cache (Step 1 loads it in a few seconds)")
except SystemExit:
    print(f"[note] victim model not cached yet; Step 1 downloads it (about 270 MB, pinned revision)")

# the shared victim-api fixture serves classifier probability rows; show why this lab serves the
# language model's logits itself (the fixture has no endpoint for full logit rows)
app = victim_api.create_app(lambda X: np.full((len(X), 2), 0.5), ["a", "b"], 3,
                            {"check": victim_api.KeyPolicy()})
with victim_api.serve(app, quiet=True) as url:
    r = victim_api.VictimClient(url, "check").predict([[0, 0, 0]], detail="logprobs")
print(f"[ok] victim-api fixture answers classifier rows ({list(r['results'][0])}); it has no endpoint")
print("     for a language model's full logit vectors, so this lab serves lantern-mini-1 locally")

pool, honest = P.load_prompt_pool()
print(f"[ok] assets/prompts.json: {len(pool)}-sentence pool, {len(honest)} honest user prompts")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
