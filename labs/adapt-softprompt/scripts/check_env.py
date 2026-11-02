"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python adapt-softprompt/scripts/check_env.py
"""
import labkit

labkit.banner()

import peft  # noqa: E402
import safetensors  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import spl  # noqa: E402

repo, rev = spl.tinylm.MODELS[spl.MODEL]
print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} peft {peft.__version__} "
      f"safetensors {safetensors.__version__}")
print(f"[ok] torch threads {torch.get_num_threads()} (spl caps at 4)")
print(f"[ok] model {repo} @ {rev[:7]} (fetched in Step 1); canary {spl.CANARY}")
print(f"[ok] task: {len(spl.TRAIN)} training rows, {len(spl.HELDOUT)} held-out rows, queues {', '.join(spl.QUEUES)}")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
print("[skip] model backend: this lab needs none")
