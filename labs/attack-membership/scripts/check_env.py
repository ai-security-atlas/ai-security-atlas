"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-membership/scripts/check_env.py
"""
import labkit

labkit.banner()

import art  # noqa: E402
import opacus  # noqa: E402
import sklearn  # noqa: E402
import torch  # noqa: E402

import mia  # noqa: E402
import vision_zoo as vz  # noqa: E402

print(f"[ok] torch {torch.__version__} opacus {opacus.__version__} adversarial-robustness-toolbox {art.__version__} "
      f"scikit-learn {sklearn.__version__}")

bad = [n for n, m in vz.manifest().items() if vz.sha256(vz.CKPT / m["file"]) != m["sha256"]]
if bad:
    print(f"[!!] vision-zoo sha256 mismatch: {' '.join(bad)} (restore with: git checkout -- _shared/vision_zoo/checkpoints)")
elif mia.TARGET not in vz.manifest():
    print(f"[!!] vision-zoo has no {mia.TARGET} (restore with: git checkout -- _shared/vision_zoo/checkpoints)")
else:
    print(f"[ok] vision-zoo target {mia.TARGET} sha256 {vz.manifest()[mia.TARGET]['sha256'][:12]} matches the manifest")

D = mia.data()
print(f"[ok] dataset {vz.DATASET}: {D['n']} members + {D['n']} non-members + {2 * D['c']} canaries, "
      f"attacker pool {len(D['pool_x'])} (bundled with scikit-learn, no download)")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
print("[skip] model backend: this lab needs none")
