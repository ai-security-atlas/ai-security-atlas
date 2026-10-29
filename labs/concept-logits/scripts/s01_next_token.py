"""Step 1: logits -> softmax -> sampling on a tiny real model. Run from labs/:
    docker compose run --rm workbench python concept-logits/scripts/s01_next_token.py
Network: the download only (huggingface.co, about 0.7 GB); later steps read the HF cache.
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402

import logitlab  # noqa: E402

PROMPT = "The capital of France is"

print(f"downloading {logitlab.MODEL_ID} @ {logitlab.REVISION[:7]} ({', '.join(logitlab.PATTERNS)})", flush=True)
tok, model = logitlab.load(download=True)
c = model.config
n = sum(p.numel() for p in model.parameters())
print(f"{type(model).__name__} {n / 1e6:.1f}M params  hidden {c.hidden_size}  vocab {c.vocab_size}  "
      f"tied unembedding {c.tie_word_embeddings}")

ids = tok(PROMPT, return_tensors="pt").input_ids
with torch.no_grad():
    logits = model(ids).logits
print(f'prompt "{PROMPT}" -> {ids.shape[1]} tokens -> logits {tuple(logits.shape)}')
z = logits[0, -1]
p = torch.softmax(z, -1)
lp = torch.log_softmax(z, -1)
print(f"softmax: p = exp(z) / sum(exp(z))   sum p = {p.sum().item():.4f}   logprob = z - {torch.logsumexp(z, -1).item():.2f}")
top = z.topk(8)
print(f"{'rank':<5} {'token':<12} {'logit':>7} {'prob':>7} {'logprob':>8}")
rows = []
for r, (v, i) in enumerate(zip(top.values, top.indices), 1):
    t = tok.decode([int(i)])
    rows.append([t, round(v.item(), 2), round(p[i].item(), 4), round(lp[i].item(), 3)])
    print(f"{r:<5} {t!r:<12} {v.item():>7.2f} {p[i].item():>7.3f} {lp[i].item():>8.3f}")

print("temperature: p_T = softmax(z / T)")
temps = {}
for T in (0.5, 1.0, 2.0):
    pt = torch.softmax(z / T, -1)
    ent = -(pt * torch.log(pt.clamp_min(1e-30))).sum().item()
    g = torch.Generator().manual_seed(0)
    s = torch.multinomial(pt, 1000, replacement=True, generator=g)
    counts = torch.bincount(s, minlength=pt.numel())
    top_tok = int(z.argmax())
    temps[str(T)] = {"p_top": round(pt[top_tok].item(), 3), "entropy": round(ent, 2),
                     "distinct": int((counts > 0).sum()), "top_hits": int(counts[top_tok])}
    print(f"T={T:<4} p(top) {pt[top_tok].item():.3f}  entropy {ent:.2f} nats  "
          f"1000 samples: {int(counts[top_tok])} x {tok.decode([top_tok])!r}, {int((counts > 0).sum())} distinct tokens")
logitlab.save("s01_next_token.json", {"prompt": PROMPT, "shape": list(logits.shape), "top": rows, "temps": temps,
                                      "hidden": c.hidden_size, "vocab": c.vocab_size})
