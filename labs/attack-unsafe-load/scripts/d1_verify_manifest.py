"""Step D1: pin a reviewed revision and verify every file before loading. Run from labs/:
    docker compose run --rm workbench python attack-unsafe-load/scripts/d1_verify_manifest.py --revision main
    docker compose run --rm workbench python attack-unsafe-load/scripts/d1_verify_manifest.py --revision v1.0

Compares the files of <revision> in the local hub with work/trusted-manifest.json (saved
when your team reviewed v1.0 in Step 8). Exits 1 and loads nothing on any mismatch.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys

import labkit

labkit.banner()

ap = argparse.ArgumentParser()
ap.add_argument("--revision", required=True, help="a tag, branch or commit of the local hub repo")
rev = ap.parse_args().revision

W = labkit.work()
HUB = W / "hub" / "acme" / "tiny-bert.git"
pinned = W / "trusted-manifest.json"
if not HUB.exists() or not pinned.exists():
    sys.exit("[!!] no hub or manifest: run Step 8 (s08_hub_setup.py) first")


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL).stdout.strip()


d = W / "verify" / "tiny-bert"
shutil.rmtree(d, ignore_errors=True)
git("clone", "-q", str(HUB), str(d))
git("checkout", "-q", rev, cwd=d)
print(f"checked out {rev} = {git('rev-parse', '--short', 'HEAD', cwd=d)}  (pinned manifest: work/{pinned.name})")

want = json.loads(pinned.read_text())
got = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.iterdir()) if p.is_file()}
bad = sorted(f for f in want.keys() | got.keys() if want.get(f) != got.get(f))
for f in sorted(want.keys() | got.keys()):
    w, g = (want.get(f) or "-")[:12], (got.get(f) or "-")[:12]
    print(f"  {'MISMATCH' if f in bad else 'ok      '} {f:<20} pinned {w:<12}  got {g}")
if bad:
    print("REFUSING TO LOAD: files differ from the reviewed manifest")
    sys.exit(1)

print("VERIFIED: every file matches the reviewed manifest")
from transformers import AutoModelForSequenceClassification  # noqa: E402

model = AutoModelForSequenceClassification.from_pretrained(d, use_safetensors=True)
print(f"loaded {type(model).__name__} from model.safetensors")
