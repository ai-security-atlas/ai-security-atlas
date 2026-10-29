"""Step 3/4 (and Steps 5, Evaluate): a victim loads acme/tiny-sentiment the way its model card says. Run from labs/:
    docker compose run --rm workbench python attack-dependency/scripts/s03_victim_load.py --revision main --trust-remote-code
    docker compose run --rm workbench python attack-dependency/scripts/s03_victim_load.py --revision main

The local hub resolves --revision (a branch, tag or commit) to a commit and checks it out, as
snapshot_download(revision=...) does. Then AutoModelForSequenceClassification.from_pretrained()
reads config.json; its auto_map names classes in .py files of the repo. With
trust_remote_code=True, transformers copies those files into its modules cache and imports them,
so their module-level code runs inside from_pretrained(), before any forward().
Without the flag the script passes trust_remote_code=False explicitly (left unset, transformers
would ask "Do you wish to run the custom code? [y/N]" in an interactive terminal).
"""
import argparse
import os
from pathlib import Path

# Set before `import labkit`, which imports transformers (it reads HF_MODULES_CACHE once, at import):
# transformers copies repo code into this folder before importing it; keep it in this lab's work dir.
os.environ["HF_MODULES_CACHE"] = str(Path(os.environ.get("ATLAS_WORK") or Path(__file__).resolve().parents[1] / "work")
                                     / "hf_modules")

import labkit  # noqa: E402
import local_hub  # noqa: E402

labkit.banner()

W = labkit.work()
os.environ["ATLAS_WORK"] = str(W)                       # the payload writes its marker here (this lab's work/)

REPO, TEXT = "acme/tiny-sentiment", "a great little model"

ap = argparse.ArgumentParser()
ap.add_argument("--revision", required=True, help="branch, tag or commit sha in the local hub")
ap.add_argument("--trust-remote-code", action="store_true")
args = ap.parse_args()

hub = local_hub.Hub(W / "hub")
if not hub.exists(REPO):
    raise SystemExit("[!!] no hub: run Step 1 (s01_hub_publish.py) first")
m = labkit.marker()
m.unlink(missing_ok=True)
folder, sha = hub.snapshot(REPO, args.revision)
kind = "commit" if local_hub.is_sha(args.revision) else "tag" if args.revision in hub.refs(REPO) and \
    args.revision != "main" else "branch"
print(f"revision {args.revision if kind != 'commit' else args.revision[:12] + '...'} ({kind}) -> commit {sha[:7]}"
      f"   files: {', '.join(p.name for p in sorted(folder.iterdir()))}")

from transformers import AutoModelForSequenceClassification  # noqa: E402

print(f"AutoModelForSequenceClassification.from_pretrained(<snapshot>, trust_remote_code={args.trust_remote_code})")
try:
    model = AutoModelForSequenceClassification.from_pretrained(folder, trust_remote_code=args.trust_remote_code)
except ValueError as e:
    lines = [ln.strip() for ln in str(e).replace(str(folder), "<snapshot>").splitlines() if ln.strip()]
    print(f"BLOCKED: ValueError: {lines[0]}")
    print(f"  {lines[-1]}")
else:
    print(f"loaded {type(model).__module__}.{type(model).__name__}")
    logits = model(model.encode(TEXT)).detach()[0]
    print(f"predict({TEXT!r}) -> {model.config.id2label[int(logits.argmax())]}  logits {[round(x, 4) for x in logits.tolist()]}")
print("marker exists:", m.exists())
