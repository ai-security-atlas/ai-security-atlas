"""Step 6 (part 1): a local package index with a real package and a typosquat. Run from labs/:
    docker compose run --rm workbench python attack-dependency/scripts/s06_build_index.py

The index is a folder (work/index/simple, the PEP 503 layout PyPI serves) that stands in for a
public index; pip reads it through a file:// URL. Nothing is uploaded anywhere.
  * acme-tokenizer 1.0.0: the helper the model card asks for (acme's real package).
  * acme-tokenizr 1.0.0: an attacker's upload one letter away. It depends on acme-tokenizer and
    re-exports it, so it works, and it ships acme_tokenizr.pth, which Python's `site` module
    processes at every interpreter start; its `import` line loads _acme_tokenizr_boot, whose body
    is the lab's inert payload, labkit.INERT_CODE, copied verbatim.
Wheels are built by hand with fixed timestamps, so their sha256 is the same on every machine.
"""
import shutil
import zipfile

import labkit
from local_hub import pypi

labkit.banner()

W = labkit.work()
for d in ("index", "dist"):
    shutil.rmtree(W / d, ignore_errors=True)
dist = W / "dist"

TOKENIZER = '''\
"""acme-tokenizer: byte ids for acme/tiny-sentiment."""
__version__ = "1.0.0"


def encode(text):
    return [b % 64 for b in text.lower().encode("utf-8")]
'''

real = pypi.build_wheel(dist, "acme-tokenizer", "1.0.0", {"acme_tokenizer/__init__.py": TOKENIZER},
                        summary="Byte tokenizer for acme models")
squat = pypi.build_wheel(dist, "acme-tokenizr", "1.0.0", {
    "acme_tokenizr/__init__.py": "from acme_tokenizer import *  # noqa: F401,F403\n",
    "acme_tokenizr.pth": "import _acme_tokenizr_boot\n",
    "_acme_tokenizr_boot.py": labkit.INERT_CODE,
}, requires=["acme-tokenizer==1.0.0"], summary="Byte tokenizer for acme models")

idx = pypi.Index(W / "index")
for whl in (real, squat):
    idx.add(whl)
idx.write()
print(f"[ok] local index {idx.url}")
for project, wheels in idx.projects().items():
    for name in wheels:
        print(f"     {project:<16} {name:<38} sha256 {pypi.sha256(dist / name)[:12]}")

print("\nacme-tokenizr wheel contents:")
z = zipfile.ZipFile(squat)
for zi in z.infolist():
    print(f"  {zi.filename:<44} {zi.file_size:>4} bytes")
print("\nacme_tokenizr.pth: " + z.read("acme_tokenizr.pth").decode().strip())
