"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python concept-embeddings/scripts/check_env.py
"""
import labkit

labkit.banner()

import safetensors  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import emblab  # noqa: E402
import tinylm  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} safetensors {safetensors.__version__}")
print(f"[ok] torch threads {torch.get_num_threads()} (emblab caps at 4)")
repo, rev = tinylm.MODELS[emblab.MODEL]
print(f"[ok] model {repo} @ {rev[:7]} (fetched in Step 1); canary {emblab.CANARY}")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
print("[skip] model backend: this lab needs none")
