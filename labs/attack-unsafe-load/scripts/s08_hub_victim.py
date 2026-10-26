"""Step 8 (part 2): a victim pulls "latest" from the local hub and loads it two ways. Run from labs/:
    docker compose run --rm workbench python attack-unsafe-load/scripts/s08_hub_victim.py

(1) transformers from_pretrained(): uses torch's weights_only default for .bin files.
(2) a hand-written "resume from checkpoint" helper with torch.load(weights_only=False),
    the kind of code that still exists in many training repos.
"""
import shutil
import subprocess

import labkit

labkit.banner()

import torch  # noqa: E402
from transformers import AutoModelForSequenceClassification, BertConfig, BertForSequenceClassification  # noqa: E402

W = labkit.work()
HUB = W / "hub" / "acme" / "tiny-bert.git"
if not HUB.exists():
    raise SystemExit("[!!] no hub: run s08_hub_setup.py first")
m = labkit.marker()


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL).stdout.strip()


repo = W / "victim" / "tiny-bert"
shutil.rmtree(repo, ignore_errors=True)
git("clone", "-q", str(HUB), str(repo))
print(f"cloned main: {git('log', '--oneline', '-1', cwd=repo)}   files: {sorted(p.name for p in repo.iterdir() if p.is_file())}")

print("\n(1) AutoModelForSequenceClassification.from_pretrained(<clone of main>)")
m.unlink(missing_ok=True)
try:
    model = AutoModelForSequenceClassification.from_pretrained(repo)
    print(f"    loaded {type(model).__name__}")
except Exception as e:
    why = next((ln.strip() for ln in str(e).splitlines() if "WeightsUnpickler error" in ln), str(e).splitlines()[0])
    print(f"    BLOCKED: {type(e).__name__}: Weights only load failed. ...")
    print(f"    {why[:120]}...")
print("    marker exists:", m.exists())

print("\n(2) resume_from_checkpoint(): torch.load(f, weights_only=False)")
m.unlink(missing_ok=True)
model = BertForSequenceClassification(BertConfig.from_pretrained(repo))
sd = torch.load(repo / "pytorch_model.bin", weights_only=False)
print(f"    load_state_dict: {model.load_state_dict(sd, strict=False)}")
print("    marker exists:", m.exists())
