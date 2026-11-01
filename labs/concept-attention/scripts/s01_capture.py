"""Step 1: capture the attention weights of SmolLM2-135M-Instruct for one prompt. Run from labs/:
    docker compose run --rm workbench python concept-attention/scripts/s01_capture.py
"""
import json
import time

import labkit

labkit.banner()

import attnlab as A  # noqa: E402

torch = A._torch()
t0 = time.time()
f = A.fixture(2, "inject")

# The default (sdpa) kernel never materializes the weights.
tok, fast = A.load("sdpa")
ids, seg, text = A.encode(tok, f["doc"], f["middle"])
with torch.no_grad():
    o = fast(input_ids=torch.tensor([ids]), output_attentions=True)
att_sdpa = o.attentions
sdpa_note = ("None" if att_sdpa is None or all(a is None for a in att_sdpa)
             else f"{len(att_sdpa)} tensors {tuple(att_sdpa[0].shape)}")
print(f"sdpa  : output_attentions=True -> attentions {sdpa_note}")
del fast

tok, model = A.load("eager")
cfg = model.config
att = A.attentions(model, ids)
print(f"eager : output_attentions=True -> attentions {len(att)} tensors {tuple(att[0].shape)} per prompt")
print(f"{A.MODEL_ID}: {cfg.num_hidden_layers} layers x {cfg.num_attention_heads} query heads "
      f"({cfg.num_key_value_heads} key/value heads), hidden {cfg.hidden_size}")

stack = torch.stack(att)                       # (L, H, T, T)
rows = stack.sum(-1)
upper = torch.triu(torch.ones(len(ids), len(ids)), 1).bool()
print(f"each row sums to 1: min {rows.min().item():.4f} max {rows.max().item():.4f}   "
      f"weight on future positions: {stack[..., upper].abs().max().item():.1e} (causal mask)")

counts = {s: seg.count(s) for s in A.SEGMENTS}
print(f"prompt {len(ids)} tokens: " + "  ".join(f"{s} {n}" for s, n in counts.items()))
print(f"middle sentence (injected): {f['middle']!r}")

last = stack[:, :, -1, :].mean((0, 1))         # generating position, mean over layers and heads
top = torch.topk(last, 8)
pieces = [A.piece(p) for p in tok.convert_ids_to_tokens(ids)]
print(f"generating position = token {len(ids) - 1} {pieces[-1]!r}; where its attention goes (mean of {cfg.num_hidden_layers * cfg.num_attention_heads} heads):")
print("rank  pos  token            segment    weight")
top_rows = []
for r, (w, k) in enumerate(zip(top.values.tolist(), top.indices.tolist()), 1):
    print(f"{r:<5} {k:<4} {pieces[k]!r:<16} {seg[k]:<10} {w:.3f}")
    top_rows.append([k, pieces[k], seg[k], round(w, 4)])
print(f"({time.time() - t0:.0f}s)")

labkit.out("s01_capture.json").write_text(json.dumps({
    "fixture": f["id"], "sdpa": sdpa_note, "shape": list(att[0].shape), "layers": cfg.num_hidden_layers,
    "heads": cfg.num_attention_heads, "kv_heads": cfg.num_key_value_heads, "n_tokens": len(ids),
    "counts": counts, "top": top_rows, "pieces": pieces, "seg": seg,
    "last_mean": [round(x, 5) for x in last.tolist()], "middle": f["middle"],
}, ensure_ascii=False) + "\n")
