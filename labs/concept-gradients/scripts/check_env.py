"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python concept-gradients/scripts/check_env.py
"""
import labkit

labkit.banner()

import opacus  # noqa: E402
import safetensors  # noqa: E402
import sklearn  # noqa: E402
import torch  # noqa: E402

import vision_zoo as vz  # noqa: E402

print(f"[ok] torch {torch.__version__} opacus {opacus.__version__} scikit-learn {sklearn.__version__} "
      f"safetensors {safetensors.__version__}")
m = vz.manifest().get("cnn-clean")
if m and vz.sha256(vz.CKPT / m["file"]) == m["sha256"]:
    print(f"[ok] vision-zoo cnn-clean sha256 {m['sha256'][:12]} matches (Step 2 retrains it and compares the weights)")
else:
    print("[!!] vision-zoo cnn-clean missing or sha256 mismatch (restore with: git checkout -- _shared/vision_zoo/checkpoints)")
d = vz.digits()
print(f"[ok] dataset {vz.DATASET}: {len(d['x_train'])} train / {len(d['x_test'])} test, bundled with scikit-learn (no download)")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
print("[skip] model backend: this lab needs none")
