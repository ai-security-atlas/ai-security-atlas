"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python concept-decoding/scripts/check_env.py
"""
import labkit

labkit.banner()

import peft  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import declab  # noqa: E402
import evalkit  # noqa: E402
import tinylm  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} peft {peft.__version__} "
      f"evalkit {evalkit.__version__}")
got = tinylm.adapter_sha256(tinylm.GUARD_DIR)
print(f"[{'ok' if got == tinylm.GUARD_SHA256 else '!!'}] tinylm guard adapter sha256 {got[:12]} "
      f"(pinned {tinylm.GUARD_SHA256[:12]})")
print(f"[ok] {declab.THREADS} CPU threads for generation (set TINYLM_THREADS to change)")
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
    print("[skip] Step 7 (no model backend; every other step runs without one)")
else:
    try:
        c = evalkit.Chat.from_env()
        ids = c.models()
        print(f"[ok] LLM endpoint {c.base_url} model {c.model} ({'listed' if c.model in ids else 'not listed: pull it first'})")
    except evalkit.ChatError as e:
        print(f"[!!] LLM endpoint unreachable ({e}); see labs/requirements.md")
