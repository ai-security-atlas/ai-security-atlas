"""Step 6 (part 2): a developer mistypes the package name. Run from labs/:
    docker compose run --rm workbench python attack-dependency/scripts/s06_victim_install.py

Creates a throwaway virtualenv in work/venv-victim (pip comes from Python's bundled ensurepip,
offline), installs `acme-tokenizr` (the typo) from the local index, then starts that venv's
Python to use the REAL package: `import acme_tokenizer`. The payload never gets imported by name:
the .pth file runs it at interpreter start.
"""
import argparse
import os
import shutil
import subprocess
import sys

import labkit
from local_hub import pypi

labkit.banner()

W = labkit.work()
os.environ["ATLAS_WORK"] = str(W)  # the payload writes its marker here (this lab's work/)

ap = argparse.ArgumentParser()
ap.add_argument("--name", default="acme-tokenizr", help="the package name the developer typed")
args = ap.parse_args()

idx = pypi.Index(W / "index")
if not idx.projects():
    raise SystemExit("[!!] no index: run s06_build_index.py first")
m = labkit.marker()
m.unlink(missing_ok=True)

venv = W / "venv-victim"
shutil.rmtree(venv, ignore_errors=True)
subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, stdin=subprocess.DEVNULL)
py = venv / "bin" / "python"

cmd = ["pip", "install", "--index-url", idx.url, args.name]
print("$ " + " ".join(cmd))
p = subprocess.run([str(py), "-m", *cmd, "--no-cache-dir", "--disable-pip-version-check", "--no-input"],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL)
for line in p.stdout.splitlines():
    if line.startswith(("Looking in", "Successfully installed", "ERROR")):
        print(line)
if p.returncode:
    print(p.stderr.strip())
print("marker exists after install:", m.exists())

site = next((venv / "lib").glob("python3*/site-packages"))
pth = sorted(f.name for f in site.glob("*.pth") if not f.name.startswith("distutils"))
print(f"site-packages/*.pth: {', '.join(pth) or 'none'}")

code = "import acme_tokenizer; print('acme_tokenizer.encode(\"great\") ->', acme_tokenizer.encode('great'))"
print("\n$ venv-victim/bin/python -c \"import acme_tokenizer; ...\"")
r = subprocess.run([str(py), "-c", code], capture_output=True, text=True, stdin=subprocess.DEVNULL)
print((r.stdout + r.stderr).strip())
print("marker exists:", m.exists())
