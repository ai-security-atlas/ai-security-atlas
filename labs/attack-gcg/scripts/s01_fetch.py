"""Step 1: download the two pinned tiny models and meet the victim. Run from labs/:
    docker compose run --rm workbench python attack-gcg/scripts/s01_fetch.py
Network: the downloads only (huggingface.co); later steps read the HF cache.
"""
import json

import labkit

labkit.banner()

import tinylm  # noqa: E402

import gcg  # noqa: E402

for name in (gcg.VICTIM, gcg.SECOND):
    repo, rev = tinylm.MODELS[name]
    print(f"downloading {repo} @ {rev[:7]} ({', '.join(tinylm.PATTERNS)})", flush=True)
    tinylm.fetch(name, download=True)
tok, model = gcg.load()
n = sum(p.numel() for p in model.parameters())
print(f"victim {type(model).__name__} {n / 1e6:.1f}M params, {model.config.num_hidden_layers} layers, "
      f"vocabulary {len(tok):,} tokens, fp32, greedy decoding")
before, after = gcg.template(tok)
print(f"chat template ({len(gcg.enc(tok, before + gcg.REQUEST + after))} tokens with the request):")
print("  " + (before + "{suffix goes here}" + after).replace("\n", "\\n"))
rep = gcg.reply(tok, model, gcg.REQUEST, max_new_tokens=40)
print(f"user: {gcg.REQUEST}\nreply: {rep}")
print(f"starts with {gcg.CANARY}: {gcg.hit(rep)}")
labkit.out("fetch.json").write_text(json.dumps({"params": n, "vocab": len(tok), "layers": model.config.num_hidden_layers,
                                                "request": gcg.REQUEST, "reply": rep}) + "\n")
