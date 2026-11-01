"""Step 1: the guardrail is a classifier. Run from labs/:
    docker compose run --rm workbench python arch-encoder/scripts/s01_guardrail.py
Loads the pinned encoder-only classifier, prints what it is, and scores 8 short injections and 12 short benign
texts. Output: two probabilities per input (SAFE, INJECTION); no text is generated.
"""
import time

import labkit

labkit.banner()

import enclab  # noqa: E402

t0 = time.time()
g = enclab.Guard()
c = g.model.config
n_params = sum(p.numel() for p in g.model.parameters())
print(f"guardrail {enclab.GUARD[0]} @ {enclab.GUARD[1][:7]}")
print(f"  {c.model_type}: {c.num_hidden_layers} layers, hidden {c.hidden_size}, {c.num_attention_heads} heads, "
      f"{n_params / 1e6:.0f}M params, vocab {c.vocab_size}")
print(f"  head: [CLS] vector -> {len(g.labels)} logits {list(g.labels.values())}; flag when P(INJECTION) >= 0.5")
print(f"  max_position_embeddings {c.max_position_embeddings}; the pipeline truncates every input to "
      f"{enclab.MAX_LEN} tokens")

inj = g.scores(enclab.INJECTIONS)
ben = g.scores(enclab.BENIGN)
rows = [("injection", t, p) for t, p in zip(enclab.INJECTIONS, inj)] + [("benign", t, p) for t, p in zip(enclab.BENIGN, ben)]
print(f"{'kind':<10} {'P(inj)':>7}  verdict    text")
for kind, t, p in rows:
    show = t if len(t) <= 66 else t[:63] + "..."
    print(f"{kind:<10} {p:7.3f}  {'INJECTION' if p >= .5 else 'SAFE':<9}  {show}")
tp = sum(p >= .5 for p in inj)
fp = sum(p >= .5 for p in ben)
print(f"short injections flagged {tp}/{len(inj)}; short benign texts flagged {fp}/{len(ben)}  ({time.time() - t0:.0f}s)")
enclab.save("s01_guardrail.json", {
    "repo": enclab.GUARD[0], "rev": enclab.GUARD[1][:7], "model_type": c.model_type, "layers": c.num_hidden_layers,
    "hidden": c.hidden_size, "heads": c.num_attention_heads, "params_m": round(n_params / 1e6), "labels": list(g.labels.values()),
    "max_len": enclab.MAX_LEN, "rows": [{"kind": k, "text": t, "p": round(p, 4)} for k, t, p in rows],
    "tp": tp, "n_inj": len(inj), "fp": fp, "n_ben": len(ben)})
