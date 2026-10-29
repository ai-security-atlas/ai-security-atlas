"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-fgsm/scripts/check_env.py
"""
import labkit

labkit.banner()

import matplotlib  # noqa: E402
import safetensors  # noqa: E402
import sklearn  # noqa: E402
import torch  # noqa: E402

import vision_zoo as vz  # noqa: E402

print(f"[ok] torch {torch.__version__} scikit-learn {sklearn.__version__} matplotlib {matplotlib.__version__} "
      f"safetensors {safetensors.__version__}")

bad = []
for name, m in vz.manifest().items():
    if vz.sha256(vz.CKPT / m["file"]) != m["sha256"]:
        bad.append(name)
if bad:
    print(f"[!!] vision-zoo sha256 mismatch: {' '.join(bad)} (restore with: git checkout -- _shared/vision_zoo/checkpoints)")
else:
    print(f"[ok] vision-zoo checkpoints sha256 match ({', '.join(vz.manifest())})")

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
