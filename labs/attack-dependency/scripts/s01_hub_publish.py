"""Step 1: a publisher ships a model whose architecture is Python code in the repo. Run from labs/:
    docker compose run --rm workbench python attack-dependency/scripts/s01_hub_publish.py

The hub is the shared local-hub fixture (labs/_shared/local_hub): bare git repos under
work/hub/. Nothing touches huggingface.co.
1. acme publishes acme/tiny-sentiment v1.0: config.json whose `auto_map` points the Auto classes
   at configuration_tinysent.py and modeling_tinysent.py, plus model.safetensors and a model card.
2. Your team reads the code at v1.0 and records the commit sha and the sha256 of every code file
   in work/reviewed.json (used by Steps 5, D1, D3 and Evaluate).
Nothing is imported or executed here: the script only writes files and reads them back.
"""
import json
import shutil

import labkit
import local_hub

labkit.banner()

import torch  # noqa: E402
from safetensors.torch import save  # noqa: E402

REPO = "acme/tiny-sentiment"
W = labkit.work()

CONFIG = {
    "architectures": ["TinySentForSequenceClassification"],
    "auto_map": {
        "AutoConfig": "configuration_tinysent.TinySentConfig",
        "AutoModelForSequenceClassification": "modeling_tinysent.TinySentForSequenceClassification",
    },
    "model_type": "tinysent",
    "vocab_size": 64,
    "hidden_size": 8,
    "num_labels": 2,
    "id2label": {"0": "negative", "1": "positive"},
    "label2id": {"negative": 0, "positive": 1},
}

CONFIGURATION_PY = '''\
"""TinySent configuration (acme/tiny-sentiment)."""
from transformers import PretrainedConfig


class TinySentConfig(PretrainedConfig):
    model_type = "tinysent"

    def __init__(self, vocab_size=64, hidden_size=8, **kwargs):
        self.vocab_size = vocab_size
        self.hidden_size = hidden_size
        super().__init__(**kwargs)
'''

MODELING_PY = '''\
"""TinySent: a bag-of-bytes sentiment classifier (acme/tiny-sentiment)."""
import torch
from torch import nn
from transformers import PreTrainedModel

from .configuration_tinysent import TinySentConfig


class TinySentForSequenceClassification(PreTrainedModel):
    config_class = TinySentConfig

    def __init__(self, config):
        super().__init__(config)
        self.embed = nn.EmbeddingBag(config.vocab_size, config.hidden_size, mode="mean")
        self.head = nn.Linear(config.hidden_size, config.num_labels)
        self.post_init()

    @staticmethod
    def encode(text):
        return torch.tensor([[b % 64 for b in text.lower().encode("utf-8")]])

    def forward(self, input_ids):
        return self.head(self.embed(input_ids))
'''

CARD = """\
# acme/tiny-sentiment

A tiny bag-of-bytes sentiment classifier. Its architecture ships as code in this repo, so load it with
`trust_remote_code=True`. Tokenize with our helper package: `pip install acme-tokenizer`.
"""


def weights():
    """Exact float32 values (multiples of 1/8), so the safetensors bytes and the commit sha are reproducible."""
    emb = ((torch.arange(64 * 8) * 5 % 7) - 3).float().reshape(64, 8) / 8
    head = ((torch.arange(2 * 8) * 3 % 5) - 2).float().reshape(2, 8) / 8
    return {"embed.weight": emb, "head.weight": head, "head.bias": torch.tensor([0.0, 0.125])}


files = {
    "README.md": CARD,
    "config.json": json.dumps(CONFIG, indent=2) + "\n",
    "configuration_tinysent.py": CONFIGURATION_PY,
    "modeling_tinysent.py": MODELING_PY,
    "model.safetensors": save(weights()),
}

for d in ("hub", "reviewed.json"):
    p = W / d
    shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
hub = local_hub.Hub(W / "hub")
hub.create(REPO)
sha = hub.push(REPO, files, "publish tiny-sentiment v1.0", tag="v1.0")
print(f"[ok] acme published {REPO} to work/hub/acme/tiny-sentiment.git, tag v1.0")
print(f"     commit {sha}")
for name in hub.files(REPO, "v1.0"):
    print(f"     {name:<28} {len(hub.show(REPO, 'v1.0', name)):>6} bytes")

cfg = json.loads(hub.show(REPO, "v1.0", "config.json"))
print("\nconfig.json auto_map (class name -> <file>.<class> in the repo):")
for auto, target in cfg["auto_map"].items():
    print(f"  {auto:<36} -> {target.split('.')[0]}.py :: {target.split('.')[1]}")

code = sorted({t.split(".")[0] + ".py" for t in cfg["auto_map"].values()})
review = {"repo": REPO, "commit": sha,
          "code": {f: local_hub.sha256_bytes(hub.show(REPO, sha, f)) for f in code}}
(W / "reviewed.json").write_text(json.dumps(review, indent=1) + "\n")
print(f"\n[ok] your team reviewed the code at v1.0 and saved work/reviewed.json:")
print(f"     commit {sha}")
for f, h in review["code"].items():
    print(f"     {f:<28} sha256 {h[:12]}")
print("\nmodel card: " + CARD.split(". ")[-1].strip())
