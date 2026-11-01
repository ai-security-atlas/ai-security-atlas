"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python transform-pruning/scripts/check_env.py
"""
import labkit

labkit.banner()

import torch  # noqa: E402
import transformers  # noqa: E402

import prunelab as pl  # noqa: E402
import tinylm  # noqa: E402
import vision_zoo as vz  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} torch.nn.utils.prune available")
man = vz.manifest()
shas, bad = [], 0
for kind, (variant, _, _) in pl.KINDS.items():
    m = man[variant]
    got = vz.sha256(vz.CKPT / m["file"])
    bad += got != m["sha256"]
    shas.append(f"{variant} {got[:12]}{'' if got == m['sha256'] else ' MISMATCH'}")
print(f"[{'!!' if bad else 'ok'}] vision-zoo backdoored CNNs {'do not match' if bad else 'match'} the manifest: "
      f"{', '.join(shas)}")
got = tinylm.adapter_sha256(tinylm.GUARD_DIR)
print(f"[{'ok' if got == tinylm.GUARD_SHA256 else '!!'}] tinylm guard adapter sha256 {got[:12]} "
      f"(pinned {tinylm.GUARD_SHA256[:12]})")
print(f"[ok] {pl.THREADS} CPU threads for the language model (set TINYLM_THREADS to change)")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
print("[skip] model backend: this lab needs none")
