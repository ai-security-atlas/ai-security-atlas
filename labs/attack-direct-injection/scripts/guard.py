"""Input classifier for LAB-06 Step D2 and Evaluate: protectai/deberta-v3-base-prompt-injection-v2.

A DeBERTa-v3 sequence classifier (labels SAFE / INJECTION), pinned to one revision and run on CPU in the
workbench. It sits in front of atlas-app: a message it labels INJECTION never reaches the bot.
"""
import warnings

import labkit  # noqa: F401  (quiets transformers)
import torch
import transformers
from huggingface_hub import snapshot_download

warnings.filterwarnings("ignore", category=FutureWarning)  # torch.jit.script deprecation inside DeBERTa

REPO = "protectai/deberta-v3-base-prompt-injection-v2"
REVISION = "90c9989b1a342275dd0d1a95aad283c04e075671"
FILES = ["config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "added_tokens.json",
         "model.safetensors"]


class Classifier:
    def __init__(self):
        path = snapshot_download(REPO, revision=REVISION, allow_patterns=FILES)
        self.tok = transformers.AutoTokenizer.from_pretrained(path)
        self.model = transformers.AutoModelForSequenceClassification.from_pretrained(path).train(False)   # inference mode
        self.labels = self.model.config.id2label

    @torch.no_grad()
    def score(self, text):
        """P(INJECTION) for one message."""
        enc = self.tok(text, return_tensors="pt", truncation=True, max_length=512)
        return self.model(**enc).logits.softmax(-1)[0][1].item()

    def flags(self, text):
        return self.score(text) >= 0.5


def message_text(t):
    """Everything the client sent in one catalogue technique (all roles), as the gate sees it."""
    return "\n".join(m["content"] for m in t["messages"])
