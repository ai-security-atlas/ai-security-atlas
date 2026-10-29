"""Step 1: download three pinned tokenizers and one small chat model. Run from labs/:
    docker compose run --rm workbench python concept-tokens/scripts/s01_fetch.py
Network: the download only (huggingface.co); every later step reads the HF cache.
"""
import labkit

labkit.banner()

from huggingface_hub import snapshot_download  # noqa: E402

import tok  # noqa: E402

for name, (repo, rev) in tok.TOKENIZERS.items():
    weights = name == tok.MODEL
    pats = tok.TOKENIZER_FILES + (["model.safetensors"] if weights else [])
    snapshot_download(repo, revision=rev, allow_patterns=pats)
    t = tok.tokenizer(name)
    tmpl = "yes" if t.chat_template else "no"
    print(f"[ok] {name:<8} {repo} @ {rev[:7]}  vocab {len(t):>6}  added tokens {len(t.added_tokens_decoder):>2}"
          f"  chat template {tmpl}{'  + weights' if weights else ''}")

m = tok.model()
n = sum(p.numel() for p in m.parameters())
print(f"{type(m).__name__} {n / 1e6:.1f}M params (the only model this lab runs)")
