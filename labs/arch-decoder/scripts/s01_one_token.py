"""Step 1: a decoder writes one token at a time, and each position sees only the tokens before it. Run from labs/:
    docker compose run --rm workbench python arch-decoder/scripts/s01_one_token.py
Downloads both pinned checkpoints (2 x 0.72 GB, config, tokenizer and model.safetensors only) on the first run.
"""
import labkit

labkit.banner()

import torch  # noqa: E402

import declab as D  # noqa: E402

clock = D.Clock()
for name in D.MODELS:
    repo, rev = D.MODELS[name]
    D.fetch(name, download=True)
    print(f"[ok] {name:<9} {repo} @ {rev[:7]}")
tok = D.tokenizer()
model = D.load("instruct")
q = D.QUESTIONS[0]
ids = tok(D.chat_text(tok, q), add_special_tokens=False)["input_ids"]
print(f"prompt: the chat transcript for {q!r}, {len(ids)} tokens")
print("step  top 3 next tokens (probability)                          picked")
steps, seq = [], list(ids)
for i in range(6):
    with torch.no_grad():
        p = model(torch.tensor([seq])).logits[0, -1].softmax(-1)
    top = p.topk(3)
    cands = [(tok.decode([j]), round(v, 3)) for v, j in zip(top.values.tolist(), top.indices.tolist())]
    seq.append(top.indices[0].item())
    steps.append(cands)
    shown = "  ".join(f"{t!r} {v:.2f}" for t, v in cands)
    print(f"{i + 1:>4}  {shown:<58} {cands[0][0]!r}")
print(f"6 forward passes, each over the whole sequence so far, wrote {tok.decode(seq[len(ids):])!r}")

# causal mask: editing a token changes the outputs at its own and later positions only
x = torch.tensor([seq])
with torch.no_grad():
    ref = model(x).logits[0]
rows = []
for where, pos in (("last", len(seq) - 1), ("middle", len(seq) // 2), ("first", 1)):
    y = x.clone()
    y[0, pos] = tok(" pelican", add_special_tokens=False)["input_ids"][0]
    with torch.no_grad():
        got = model(y).logits[0]
    diff = (got - ref).abs().amax(-1)
    before = diff[:pos].max().item() if pos else 0.0
    changed = int((diff[pos:] > 1e-4).sum())
    rows.append({"edit": where, "pos": pos, "before": before, "changed": changed, "after_n": len(seq) - pos})
print(f"causal check on {len(seq)} positions: replace one token with ' pelican', compare every position's logits")
print("edit      position  max change before it  positions changed from it on")
for r in rows:
    print(f"{r['edit']:<9} {r['pos']:>8}  {r['before']:>20.1e}  {r['changed']:>4} / {r['after_n']}")
ok = all(r["before"] == 0.0 for r in rows)
print("earlier positions never change: each token sees only what came before it" if ok
      else "[!!] an earlier position changed: this is not a causal decoder")
print(clock)
D.save("s01_one_token.json", {"prompt_tokens": len(ids), "question": q, "steps": steps,
                              "written": tok.decode(seq[len(ids):]), "causal": rows, "causal_ok": ok})
