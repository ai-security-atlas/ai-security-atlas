"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-model-imitation/scripts/check_env.py
"""
from importlib.metadata import version

import labkit

labkit.banner()

import numpy as np  # noqa: E402
import torch  # noqa: E402
from sklearn.datasets import load_digits  # noqa: E402

import victim_api  # noqa: E402

print(f"[ok] torch {torch.__version__}  scikit-learn {version('scikit-learn')}  safetensors {version('safetensors')}")
print(f"[ok] fastapi {version('fastapi')}  uvicorn {version('uvicorn')}  httpx {version('httpx')}")
d = load_digits()
print(f"[ok] digits dataset bundled with scikit-learn: {d.data.shape[0]} images of {d.data.shape[1]} pixels (no download)")

app = victim_api.create_app(lambda X: np.full((len(X), 2), 0.5), ["a", "b"], 3, {"check": victim_api.KeyPolicy()})
with victim_api.serve(app, quiet=True) as url:
    r = victim_api.VictimClient(url, "check").predict([[0, 0, 0]], detail="probs")
print(f"[ok] victim-api fixture: served {r['results'][0]} on 127.0.0.1 inside the container")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
