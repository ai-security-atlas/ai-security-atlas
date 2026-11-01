"""Step 1: open SmolLM2-135M's embedding table, check that input and output embeddings are tied, and list
nearest-neighbor tokens. Run from labs/:
    docker compose run --rm workbench python concept-embeddings/scripts/s01_table.py
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402

import emblab  # noqa: E402
import tinylm  # noqa: E402

repo, rev = tinylm.MODELS[emblab.MODEL]
print(f"fetching {repo} @ {rev[:7]} (*.json, merges.txt, vocab.json, model.safetensors)")
tinylm.fetch(emblab.MODEL, download=True)
tok, model = emblab.load()
E = emblab.table(model)
total = sum(p.numel() for p in model.parameters())
emb = model.model.embed_tokens.weight
tied = model.lm_head.weight is emb
print(f"{type(model).__name__} {total / 1e6:.1f}M params  embed_tokens {tuple(E.shape)}  "
      f"= {E.numel() / 1e6:.1f}M params ({100 * E.numel() / total:.0f}%)")
print(f"tied: lm_head.weight is embed_tokens.weight -> {tied}  "
      f"(same storage {model.lm_head.weight.data_ptr() == emb.data_ptr()}, "
      f"config.tie_word_embeddings {model.config.tie_word_embeddings})")

enc = tok("The capital of France is", return_tensors="pt")
with torch.no_grad():
    h = model.model(**enc).last_hidden_state[0, -1]
    z = model.lm_head(h)
diff = (z - h @ E.T).abs().max().item()
top = z.argmax().item()
print(f"logits = h @ E.T : max |difference| {diff:.1e}; top next token {emblab.tok_str(tok, top)!r}")

st = emblab.stats(model)
print(f"row norms: min {st['n_min']:.2f}  p0.1 {st['n_lo']:.2f}  median {st['n_med']:.2f}  "
      f"p99.9 {st['n_hi']:.2f}  max {st['n_max']:.2f}")

words = [" Paris", " king", " happy", " password", " secret"]
neigh = {}
print("token         nearest rows by cosine (the token itself is rank 0, skipped)")
for w in words:
    ids = tok(w, add_special_tokens=False)["input_ids"]
    assert len(ids) == 1, (w, ids)
    nid, cos = emblab.nearest(model, E[ids], k=6)
    row = [(emblab.tok_str(tok, i), round(c, 3)) for i, c in zip(nid[0, 1:].tolist(), cos[0, 1:].tolist())]
    neigh[w] = row
    print(f"{w!r:<13} " + "  ".join(f"{t!r} {c:.2f}" for t, c in row))

labkit.out("s01_table.json").write_text(json.dumps({
    "model": repo, "params": total, "layers": model.config.num_hidden_layers, "shape": list(E.shape), "tied": tied, "logit_diff": diff,
    "top": emblab.tok_str(tok, top), "norms": {k: round(v, 3) for k, v in st.items() if isinstance(v, float)},
    "neighbors": neigh}, indent=1))
