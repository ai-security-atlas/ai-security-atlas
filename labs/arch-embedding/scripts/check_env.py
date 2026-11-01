"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python arch-embedding/scripts/check_env.py
"""
import labkit

labkit.banner()

import numpy  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import emb  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} numpy {numpy.__version__}")
for name, (repo, rev, _) in (("bi-encoder", emb.BI), ("cross-encoder", emb.CROSS)):
    print(f"[ok] {name}: {repo} @ {rev[:7]}")
print(f"[ok] {emb.THREADS} CPU threads (set TINYLM_THREADS to change), canary {emb.CANARY}")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
info = emb.app_wait()
cols = {c["id"]: c for c in info["collections"]}
plug = emb.app_get("/healthz").get("plugins", {}).get("arch-embedding")
if emb.CLEAN in cols and emb.PLANTED in cols:
    print(f"[ok] atlas-app RAG ready at {emb.URL}: embedder {info['embedder']}, {emb.CLEAN} {cols[emb.CLEAN]['chunks']} "
          f"chunks, {emb.PLANTED} {cols[emb.PLANTED]['chunks']} chunks")
    print(f"[ok] plug-in arch-embedding: collections {' '.join(plug['collections']) if plug else '?'}")
else:
    print("[!!] atlas-app runs but this lab's collections are missing; check GET /healthz plugin_errors")
