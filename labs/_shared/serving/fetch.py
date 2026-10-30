"""Fetch the pinned serving model into the HF cache and check its sha256 (the `serving-model` service).

    python -m serving.fetch                 # what compose runs before llama-server starts
    python -m serving.fetch --check         # verify only, never download

Downloads exactly one file at a pinned revision (no other repo files) into HF_HOME (/cache/hf,
the shared hf-cache-v1 volume), then hashes it. A hash mismatch exits 1, so llama-server never
starts on a file that is not the pinned one.
"""

import hashlib
import os
import sys
from pathlib import Path

from serving import MODEL, model_path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv) -> int:
    path = model_path()
    if not path.exists():
        if "--check" in argv:
            print(f"[!!] {path} is missing")
            return 1
        from huggingface_hub import hf_hub_download
        print(f"[serving] downloading {MODEL['repo']} @ {MODEL['revision'][:7]} {MODEL['file']} "
              f"({MODEL['size'] / 1e6:.0f} MB)", flush=True)
        got = Path(hf_hub_download(MODEL["repo"], MODEL["file"], revision=MODEL["revision"],
                                   cache_dir=os.path.join(os.environ.get("HF_HOME", "/cache/hf"), "hub")))
        if got.resolve() != path.resolve():
            print(f"[!!] downloaded to {got}, expected {path}")
            return 1
    digest = sha256(path)
    if digest != MODEL["sha256"]:
        print(f"[!!] sha256 mismatch for {path}: got {digest}, pinned {MODEL['sha256']}")
        return 1
    print(f"[serving] ok {path} sha256 {digest[:12]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
