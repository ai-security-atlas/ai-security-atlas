"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python concept-residual/scripts/check_env.py
"""
import labkit

labkit.banner()

import safetensors  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import residlab as rl  # noqa: E402

tinylm = rl.tinylm
print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} safetensors {safetensors.__version__}")
got = tinylm.adapter_sha256(tinylm.GUARD_DIR)
ok = got == tinylm.GUARD_SHA256
print(f"[{'ok' if ok else '!!'}] stand-in policy: {tinylm.MODELS[rl.MODEL][0]} + guard adapter {got[:12]} "
      f"({'matches' if ok else 'does not match'} the tinylm pin {tinylm.GUARD_SHA256[:12]}), canary {rl.CANARY}")
asks, ben = rl.probes()
a_dir, b_dir = rl.dir_prompts()
overlap = set(asks + ben) & set(a_dir + b_dir)
print(f"[{'ok' if not overlap else '!!'}] prompts: {len(a_dir)} + {len(b_dir)} to find the direction, "
      f"{len(asks)} + {len(ben)} held-out probes, overlap {len(overlap)}")
print(f"[ok] {rl.THREADS} CPU threads for the model (set TINYLM_THREADS to change)")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
print("[skip] model backend: this lab needs none")
