"""Step 1: download the pinned models and tokenizers, meet the victim, and watch it stop. Run from labs/:
    docker compose run --rm workbench python attack-sponge/scripts/s01_fetch.py
Network: the downloads only (huggingface.co); later steps read the HF cache.
"""
import json

import labkit

labkit.banner()

import tinylm  # noqa: E402

import sponge  # noqa: E402

for name, note in ((sponge.VICTIM, "the victim"), (sponge.SECOND, "the transfer target")):
    repo, rev = tinylm.MODELS[name]
    print(f"downloading {repo} @ {rev[:7]} ({', '.join(tinylm.PATTERNS)})", flush=True)
    tinylm.fetch(name, download=True)
for name in ("qwen2.5", "gpt2"):
    repo, rev = sponge.TOKENIZERS[name]
    print(f"downloading {repo} @ {rev[:7]} (tokenizer files only, no weights)", flush=True)
    sponge.fetch_tokenizer(name)

tok, model = sponge.load()
n = sum(p.numel() for p in model.parameters())
eos = tok.decode([tok.eos_token_id])
print(f"victim {type(model).__name__} {n / 1e6:.1f}M params, {model.config.num_hidden_layers} layers, "
      f"vocabulary {len(tok):,} tokens, fp32, greedy decoding")
print(f"stop token: {eos!r} (id {tok.eos_token_id}) ends every reply")
before, after = sponge.template(tok)
n_tpl = len(sponge.enc(tok, before + sponge.REQUEST + after))
print(f"chat template ({n_tpl} tokens with the request):")
print("  " + (before + "{suffix goes here}" + after).replace("\n", "\\n"))

clean = sponge.generate(tok, model, sponge.REQUEST, max_new_tokens=sponge.CAP)
print(f"\nuser: {sponge.REQUEST}")
print(f"reply ({clean['n_out']} tokens, stopped at {eos!r}: {clean['stopped']}): {clean['reply']!r}")
print(f"carries {sponge.CANARY}: {sponge.CANARY in clean['reply']}")

nat = sponge.generate(tok, model, sponge.P["natural_sponge"], max_new_tokens=48)
print(f"\nnatural sponge check, user: {sponge.P['natural_sponge']}")
print(f"reply tokens: {nat['n_out']}/48 (stopped: {nat['stopped']})  reply: {nat['reply'][:60]!r}")

labkit.out("fetch.json").write_text(json.dumps({
    "params": n, "vocab": len(tok), "layers": model.config.num_hidden_layers,
    "eos": eos, "eos_id": tok.eos_token_id, "template_tokens": n_tpl,
    "request": sponge.REQUEST, "reply": clean["reply"], "reply_tokens": clean["n_out"],
    "natural_sponge": sponge.P["natural_sponge"], "natural_tokens": nat["n_out"],
    "natural_cap": 48, "cap": sponge.CAP}) + "\n")
print(f"-> work/fetch.json")
