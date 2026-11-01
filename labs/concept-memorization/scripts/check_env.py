"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python concept-memorization/scripts/check_env.py
"""
import labkit

labkit.banner()

import opacus  # noqa: E402
import peft  # noqa: E402
import scipy  # noqa: E402
import torch  # noqa: E402
import transformers  # noqa: E402

import evalkit  # noqa: E402
import memlab as M  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} peft {peft.__version__} "
      f"opacus {opacus.__version__} scipy {scipy.__version__} evalkit {evalkit.__version__}")
book = labkit.inp("assets/alice.txt")
sha = __import__("hashlib").sha256(book.read_bytes()).hexdigest()
print(f"[{'ok' if sha.startswith(M.BOOK_SHA256) else '!!'}] corpus assets/alice.txt {book.stat().st_size:,} bytes, "
      f"sha256 {sha[:12]} (pinned {M.BOOK_SHA256})")
print(f"[ok] {len(M.canaries())} canaries, template {M.TEMPLATE!r}")
print(f"[ok] {M.THREADS} CPU threads for training (set TINYLM_THREADS to change)")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
