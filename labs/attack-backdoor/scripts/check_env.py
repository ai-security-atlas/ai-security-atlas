"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-backdoor/scripts/check_env.py
"""
import labkit

labkit.banner()

import art  # noqa: E402
import sklearn  # noqa: E402
import torch  # noqa: E402

import bd  # noqa: E402
import vision_zoo as vz  # noqa: E402

print(f"[ok] torch {torch.__version__} adversarial-robustness-toolbox {art.__version__} scikit-learn {sklearn.__version__}")

man = vz.manifest()
need = [bd.CLEAN] + [v for v, _, _ in bd.KINDS.values()]
missing = [n for n in need if n not in man]
bad = [n for n in need if n in man and vz.sha256(vz.CKPT / man[n]["file"]) != man[n]["sha256"]]
if missing or bad:
    print(f"[!!] vision-zoo problem: missing {missing} sha256 mismatch {bad} "
          "(restore with: git checkout -- _shared/vision_zoo/checkpoints)")
else:
    shas = ", ".join(n + " " + man[n]["sha256"][:12] for n in need)
    print(f"[ok] vision-zoo models sha256 match the manifest: {shas}")

d = bd.digits()
print(f"[ok] dataset {vz.DATASET}: {len(d['y_train'])} train / {len(d['y_test'])} test digits (bundled with scikit-learn, no download)")
print(f"[ok] target class {bd.TARGET} = {bd.CANARY}; poison rate {bd.RATE:.0%} ({len(bd.tz.poison_indices())} images)")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
print("[skip] model backend: this lab needs none")
