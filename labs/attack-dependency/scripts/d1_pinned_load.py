"""Step D1: a loading policy: no remote code unless it is the exact commit you reviewed. Run from labs/:
    docker compose run --rm workbench python attack-dependency/scripts/d1_pinned_load.py --revision main
    docker compose run --rm workbench python attack-dependency/scripts/d1_pinned_load.py --revision <reviewed sha>

1. The revision must be a full 40-hex commit sha (a branch or tag can be moved under you).
2. The code files that config.json's auto_map points to must hash to the values in
   work/reviewed.json (what your team read in Step 1).
Only then is trust_remote_code=True passed, for that snapshot only. Otherwise the script refuses
before anything is imported and exits 1. On the hub, the same rule is from_pretrained(repo,
revision=<sha>, code_revision=<sha>, trust_remote_code=True).
"""
import argparse
import json
import os
import sys
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
ap.add_argument("--revision", required=True)
rev = ap.parse_args().revision

hub = local_hub.Hub(W / "hub")
reviewed_file = W / "reviewed.json"
if not hub.exists(REPO) or not reviewed_file.exists():
    sys.exit("[!!] run Step 1 (s01_hub_publish.py) first")
reviewed = json.loads(reviewed_file.read_text())
m = labkit.marker()
m.unlink(missing_ok=True)


def refuse(why):
    print(f"REFUSED: {why}")
    print("marker exists:", m.exists())
    sys.exit(1)


if not local_hub.is_sha(rev):
    refuse(f"{rev!r} is a branch or tag name; pin a full 40-character commit sha")
sha = hub.resolve(REPO, rev)
if not sha:
    refuse(f"commit {rev[:12]} is not in {REPO} (work/reviewed.json pins {reviewed['commit']})")
print(f"pinned commit {sha[:7]}")
cfg = json.loads(hub.show(REPO, sha, "config.json"))
code = sorted({t.split(".")[0] + ".py" for t in cfg.get("auto_map", {}).values()})
bad = []
for f in code:
    got = local_hub.sha256_bytes(hub.show(REPO, sha, f))
    want = reviewed["code"].get(f)
    print(f"  {'ok      ' if got == want else 'MISMATCH'} {f:<28} reviewed {(want or '-')[:12]:<12}  got {got[:12]}")
    if got != want:
        bad.append(f)
if bad:
    refuse("remote code differs from the reviewed code")

folder, _ = hub.snapshot(REPO, sha)
from transformers import AutoModelForSequenceClassification  # noqa: E402

model = AutoModelForSequenceClassification.from_pretrained(folder, trust_remote_code=True)
logits = model(model.encode(TEXT)).detach()[0]
print(f"VERIFIED: loaded {type(model).__name__} from the reviewed commit with trust_remote_code=True")
print(f"predict({TEXT!r}) -> {model.config.id2label[int(logits.argmax())]}  logits {[round(x, 4) for x in logits.tolist()]}")
print("marker exists:", m.exists())
