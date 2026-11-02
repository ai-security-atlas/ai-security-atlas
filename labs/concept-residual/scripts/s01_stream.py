"""Step 1: the residual stream is a running sum, and you can read it at any depth. Run from labs/:
    docker compose run --rm workbench python concept-residual/scripts/s01_stream.py
Downloads SmolLM2-135M-Instruct (pinned revision) on first run and loads the stand-in policy model. For one plain
text prompt it records the embedding and every attention and MLP output, rebuilds the last block's output as
their sum, and decodes the stream after every block through the model's own final norm and output layer
(the logit lens). Writes work/stream.json.
"""
import labkit

labkit.banner()

import residlab as rl  # noqa: E402

t = rl.torch()
clock = rl.Timer()
tok, model = rl.load_guard(download=True)
layers = model.model.layers
n_layers, d_model = len(layers), model.config.hidden_size
TEXT = "The Eiffel Tower is in the city of"
TARGET = " Paris"
target_id = tok.encode(TARGET, add_special_tokens=False)
assert len(target_id) == 1, target_id
target_id = target_id[0]

enc = tok(TEXT, return_tensors="pt")
writes = {}


def keep(name):
    def f(mod, args, o):
        writes[name] = (o[0] if isinstance(o, tuple) else o).detach()
    return f


hooks = []
for i, blk in enumerate(layers):
    hooks += [blk.self_attn.register_forward_hook(keep(f"attn{i}")), blk.mlp.register_forward_hook(keep(f"mlp{i}"))]
stream, logits = rl.stream(model, enc)
for h in hooks:
    h.remove()
s = stream[:, 0, -1]  # [layers+1, d] at the last token

# 1. The stream is a sum: embedding + every attention write + every MLP write.
rebuilt = stream[0, 0].clone()
step_err = 0.0
for i in range(n_layers):
    rebuilt = rebuilt + writes[f"attn{i}"][0] + writes[f"mlp{i}"][0]
    step_err = max(step_err, float((stream[i] + writes[f"attn{i}"] + writes[f"mlp{i}"] - stream[i + 1]).abs().max()))
sum_err = float((rebuilt - stream[-1, 0]).abs().max())
write_norm = [float((writes[f"attn{i}"][0, -1] + writes[f"mlp{i}"][0, -1]).norm()) for i in range(n_layers)]
print(f"prompt {TEXT!r}: {enc['input_ids'].shape[1]} tokens, residual width {d_model}, {n_layers} blocks "
      f"x 2 writes (attention, MLP)")
print(f"block i output = block i input + attention write + MLP write: largest gap {step_err:.1e} over all "
      f"{n_layers} blocks")
print(f"embedding + {2 * n_layers} writes = last block output: largest gap {sum_err:.1e}")

# 2. Logit lens: decode the stream at every depth with the model's own final norm and output layer.
rows = []
with t.no_grad():
    for i in range(n_layers + 1):
        p = rl.lens(model, s[i]).softmax(-1)
        top = int(p.argmax())
        rank = int((p > p[target_id]).sum()) + 1
        rows.append({"layer": i, "top": tok.decode([top]), "p_top": float(p[top]), "p_target": float(p[target_id]),
                     "rank": rank, "norm": float(s[i].norm()), "write": write_norm[i - 1] if i else None})
lens_gap = float((rl.lens(model, s[-1]) - logits[0, -1]).abs().max())
first = next((r["layer"] for r in rows if r["top"] == TARGET and all(x["top"] == TARGET for x in rows[r["layer"]:])),
             None)
print(f"logit lens: stream after block L -> final norm -> lm_head ({model.config.vocab_size:,} logits); at L={n_layers} "
      f"it equals the model's output (largest gap {lens_gap:.1e})")
print(f"{'L':>3}  {'|h|':>7}  {'top token':<12} {'p(top)':>7}  {'p(Paris)':>9} {'rank':>6}")
show = sorted({0, 4, 8, 12, 16, 20, 24, 26, 27, 28, 29, 30} | ({first} if first is not None else set()))
for r in rows:
    if r["layer"] in show:
        print(f"{r['layer']:>3}  {r['norm']:7.1f}  {r['top']!r:<12} {r['p_top']:7.3f}  {r['p_target']:9.4f} {r['rank']:>6,}")
grow = rows[-1]["norm"] / rows[1]["norm"]
rl.jdump("stream.json", {"text": TEXT, "target": TARGET, "tokens": int(enc["input_ids"].shape[1]),
                         "d_model": d_model, "layers": n_layers, "step_err": step_err, "sum_err": sum_err,
                         "lens_gap": lens_gap, "first": first, "rows": rows, "repo": rl.tinylm.MODELS[rl.MODEL][0]})
where = f"from layer {first} on" if first is not None else "at no layer"
verdict = "is a sum" if max(step_err, sum_err) < 1e-3 else "is NOT a sum"
print(f"RESULT the stream {verdict} (gap {sum_err:.1e}); {TARGET!r} is the lens's top token {where}, "
      f"|h| grows {grow:.0f}x from block 1 to block {n_layers} ({clock})")
