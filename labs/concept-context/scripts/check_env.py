"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python concept-context/scripts/check_env.py
"""
import labkit

labkit.banner()

import torch  # noqa: E402
import transformers  # noqa: E402

import ctxlab  # noqa: E402
import evalkit  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} evalkit {evalkit.__version__}")
print(f"[ok] {ctxlab.THREADS} CPU threads for generation (set TINYLM_THREADS to change)")
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
    print("[skip] Step 5 (no model backend; every other step runs without one)")
else:
    c = evalkit.Chat.from_env()
    info = evalkit.ollama_info(c.base_url, c.model)
    if not info["ollama"]:
        print(f"[!!] {c.base_url} is not an Ollama server; Step 5 needs Ollama's native /api/chat (num_ctx)")
    elif not info["digest"]:
        print(f"[!!] Ollama {info['ollama']} has no model {c.model}; pull it first (ollama pull {c.model})")
    else:
        print(f"[ok] Ollama {info['ollama']} at {evalkit.client.ollama_root(c.base_url)} model {c.model} "
              f"(digest {info['digest']})")
