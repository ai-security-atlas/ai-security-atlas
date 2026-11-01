"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python arch-encoder/scripts/check_env.py
"""
import labkit

labkit.banner()

import torch  # noqa: E402
import transformers  # noqa: E402

import enclab  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__}")
for name, (repo, rev, _) in (("guardrail", enclab.GUARD), ("summarizer", enclab.SUMMARIZER)):
    print(f"[ok] {name}: {repo} @ {rev[:7]}")
print(f"[ok] {enclab.THREADS} CPU threads (set TINYLM_THREADS to change), canary {enclab.CANARY}")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
