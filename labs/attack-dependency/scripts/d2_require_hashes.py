"""Step D2: install from a hash-pinned lock file, never from a typed name. Run from labs/:
    docker compose run --rm workbench python attack-dependency/scripts/d2_require_hashes.py

Writes three inputs, then runs pip with --require-hashes in a fresh throwaway venv (work/venv-locked):
  work/requirements.lock      acme-tokenizer==1.0.0 --hash=sha256:<the wheel your team reviewed>
  work/requirements-pr.txt    a teammate's change: acme-tokenizr==1.0.0, with no hash
  work/index-mirror/          a compromised mirror serving a different acme-tokenizer 1.0.0
                              (same name and version, the payload added in a .pth)
(a) the PR file: pip refuses, because a requirement has no hash.
(b) the lock file against the compromised mirror: pip refuses, because the bytes differ.
(c) the lock file against the real index: installs; then the venv's Python starts clean.
Also used by Step D3 (the lock and PR files) and Evaluate.
"""
import os
import shutil
import subprocess
import sys

import labkit
from local_hub import pypi

labkit.banner()

W = labkit.work()
os.environ["ATLAS_WORK"] = str(W)  # the payload writes its marker here (this lab's work/)

idx, real = pypi.Index(W / "index"), W / "dist" / "acme_tokenizer-1.0.0-py3-none-any.whl"
if not real.exists() or not idx.projects():
    sys.exit("[!!] run Step 6 (s06_build_index.py) first")

lock = W / "requirements.lock"
lock.write_text(f"acme-tokenizer==1.0.0 \\\n    --hash=sha256:{pypi.sha256(real)}\n")
pr = W / "requirements-pr.txt"
pr.write_text("acme-tokenizr==1.0.0\n")

# the compromised mirror: same file name, different bytes
mirror = pypi.Index(W / "index-mirror")
shutil.rmtree(mirror.root, ignore_errors=True)
TOKENIZER = "__version__ = '1.0.0'\n\n\ndef encode(text):\n    return [b % 64 for b in text.lower().encode('utf-8')]\n"
evil = pypi.build_wheel(W / "dist-mirror", "acme-tokenizer", "1.0.0", {
    "acme_tokenizer/__init__.py": TOKENIZER,
    "acme_tokenizer_init.pth": "import _acme_tokenizer_boot\n",
    "_acme_tokenizer_boot.py": labkit.INERT_CODE,
})
mirror.add(evil)
mirror.write()
print(f"work/requirements.lock:   acme-tokenizer==1.0.0 --hash=sha256:{pypi.sha256(real)[:12]}...")
print(f"work/requirements-pr.txt: {pr.read_text().strip()}")
print(f"work/index-mirror:        acme_tokenizer-1.0.0-py3-none-any.whl sha256 {pypi.sha256(evil)[:12]}...")

m = labkit.marker()
m.unlink(missing_ok=True)
venv = W / "venv-locked"
shutil.rmtree(venv, ignore_errors=True)
subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, stdin=subprocess.DEVNULL)
py = str(venv / "bin" / "python")


def pip(label, index, req):
    shown = f"pip install --require-hashes --index-url {index.url} -r work/{req.name}"
    print(f"\n({label}) $ {shown}")
    p = subprocess.run([py, "-m", "pip", "install", "--require-hashes", "--index-url", index.url, "-r", str(req),
                        "--no-cache-dir", "--disable-pip-version-check", "--no-input"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    keep = ("ERROR", "Successfully installed", "    acme", "        Expected", "             Got")
    for line in (p.stdout + p.stderr).splitlines():
        if line.startswith(keep):
            if line.startswith("ERROR"):
                line = line.split(". ")[0] + "."
            elif " from file://" in line:
                line = line.split(" from file://")[0] + " from the index:"
            print("  " + line.rstrip())
    print(f"  exit {p.returncode}; marker exists: {m.exists()}")


pip("a", idx, pr)
pip("b", mirror, lock)
pip("c", idx, lock)
r = subprocess.run([py, "-c", "import acme_tokenizer; print('acme_tokenizer', acme_tokenizer.__version__, 'imported')"],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL)
print("  $ venv-locked/bin/python -c 'import acme_tokenizer'\n  " + (r.stdout + r.stderr).strip())
print("marker exists:", m.exists())
