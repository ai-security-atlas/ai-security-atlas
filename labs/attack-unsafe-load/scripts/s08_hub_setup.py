"""Step 8 (part 1): a publisher, a local "hub" and an attacker with push access. Run from labs/:
    docker compose run --rm workbench python attack-unsafe-load/scripts/s08_hub_setup.py

The hub is a bare git repo in work/hub/acme/tiny-bert.git. Nothing touches huggingface.co.
1. acme publishes a tiny random-init BERT (config.json + model.safetensors), tags v1.0.
2. Your team reviews v1.0 and saves its sha256 manifest (used in Step D1).
3. The attacker pushes "v1.1": the same weights as pytorch_model.bin, carrying labkit.INERT_CODE.
"""
import hashlib
import json
import shutil
import subprocess
from collections import OrderedDict
from pathlib import Path

import labkit

labkit.banner()

import torch  # noqa: E402
from safetensors.torch import load_file  # noqa: E402
from transformers import BertConfig, BertForSequenceClassification  # noqa: E402


class Payload:
    def __reduce__(self):
        # On unpickling, pickle calls builtins.exec(INERT_CODE).
        return (exec, (labkit.INERT_CODE,))


W = labkit.work()
HUB = W / "hub" / "acme" / "tiny-bert.git"


def git(*args, cwd=None, who="acme"):
    cmd = ["git", "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main",
           "-c", f"user.name={who}", "-c", f"user.email={who}@hub.invalid", *args]
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL).stdout.rstrip()


def manifest(d):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(d).iterdir()) if p.is_file()}


for d in ("hub", "publisher", "attacker"):
    shutil.rmtree(W / d, ignore_errors=True)
HUB.parent.mkdir(parents=True)
git("init", "-q", "--bare", str(HUB))

# 1. acme publishes v1.0
pub = W / "publisher" / "tiny-bert"
git("clone", "-q", str(HUB), str(pub))
remote = git("remote", "get-url", "origin", cwd=pub)
assert remote.startswith("/") and Path(remote) == HUB, f"hub remote must be a local path, got {remote}"
torch.manual_seed(0)
cfg = BertConfig(vocab_size=128, hidden_size=32, num_hidden_layers=2, num_attention_heads=2,
                 intermediate_size=64, max_position_embeddings=64, num_labels=2)
BertForSequenceClassification(cfg).save_pretrained(pub)
git("add", "-A", cwd=pub)
git("commit", "-q", "-m", "publish tiny-bert v1.0", cwd=pub)
git("tag", "v1.0", cwd=pub)
git("push", "-q", "origin", "main", "v1.0", cwd=pub)
print(f"[ok] acme published {sorted(p.name for p in pub.iterdir() if p.is_file())} to work/hub/acme/tiny-bert.git, tag v1.0")

# 2. your team reviews v1.0 and pins its manifest
(W / "trusted-manifest.json").write_text(json.dumps(manifest(pub), indent=1) + "\n")
print("[ok] your team reviewed v1.0 and saved work/trusted-manifest.json")

# 3. the attacker (push access) swaps the weights for a pickle carrying the payload
atk = W / "attacker" / "tiny-bert"
git("clone", "-q", str(HUB), str(atk))
sd = OrderedDict(load_file(atk / "model.safetensors"))  # identical weights
sd._metadata = {"__canary__": Payload()}
torch.save(sd, atk / "pytorch_model.bin")
git("rm", "-q", "model.safetensors", cwd=atk)
git("add", "-A", cwd=atk)
git("commit", "-q", "-m", "v1.1: switch to .bin for older runtimes", cwd=atk, who="acme-ci")
git("push", "-q", "origin", "main", cwd=atk)

print("\n$ git log --oneline main   (SHAs differ on every run)")
print(git("log", "--oneline", "main", cwd=str(HUB)))
print("\n$ git diff --stat v1.0 main")
print(git("diff", "--stat", "-M", "v1.0", "main", cwd=str(HUB)))
