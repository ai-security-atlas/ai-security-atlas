"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python concept-tokens/scripts/check_env.py
"""
import labkit

labkit.banner()

import tokenizers  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

print(f"[ok] torch {torch.__version__}  transformers {transformers.__version__}  tokenizers {tokenizers.__version__}")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
print("[ok] model backend: none needed (every step runs local tokenizers and SmolLM2-360M-Instruct)")
