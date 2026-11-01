"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python concept-parameters/scripts/check_env.py
"""
import labkit

labkit.banner()

import safetensors  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import paramlab as pl  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} safetensors {safetensors.__version__}")
pin = pl.pinned()
repo, rev = pl.tinylm.MODELS[pl.MODEL]
ok = pin["repo"] == repo and pin["revision"] == rev
print(f"[{'ok' if ok else '!!'}] pinned manifest: {len(pin['files'])} files of {repo} @ {rev[:12]} "
      f"(model.safetensors {pl.short(pin['files']['model.safetensors'])})")
print(f"[ok] {pl.THREADS} CPU threads for the model (set TINYLM_THREADS to change)")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
print("[skip] model backend: this lab needs none")
