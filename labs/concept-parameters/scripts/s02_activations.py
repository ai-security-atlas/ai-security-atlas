"""Step 2: run two prompts through the same weights and record the activations with forward hooks. Run from labs/:
    docker compose run --rm workbench python concept-parameters/scripts/s02_activations.py
A read-only forward hook on each of the 30 decoder blocks copies the block's output (the residual stream, one
576-number vector per token). The weights are hashed before and after both prompts.
"""
import labkit

labkit.banner()

import paramlab as pl  # noqa: E402

t = pl.torch()
clock = pl.Timer()
tok, model = pl.load()
blocks = model.model.layers
before = pl.state_sha256(model)
n_weights = sum(p.numel() for p in model.parameters())

caught = {}


def recorder(i):
    def record(mod, args, output):
        h = output[0] if isinstance(output, tuple) else output
        caught[i] = h.detach()[0].clone()
    return record


handles = [b.register_forward_hook(recorder(i)) for i, b in enumerate(blocks)]


def run(text):
    caught.clear()
    enc = tok(text, return_tensors="pt")
    with t.no_grad():
        logits = model(**enc).logits[0, -1]
    return enc["input_ids"][0].tolist(), [caught[i] for i in range(len(blocks))], logits


ids_a, acts_a, log_a = run(pl.PROMPT_A)
ids_b, acts_b, log_b = run(pl.PROMPT_B)
_, acts_a2, _ = run(pl.PROMPT_A)
for h in handles:
    h.remove()
after = pl.state_sha256(model)

cos = t.nn.functional.cosine_similarity
rows = []
for i in range(len(blocks)):
    ma, mb = acts_a[i].mean(0), acts_b[i].mean(0)
    rows.append({"layer": i, "norm_a": float(acts_a[i][-1].norm()), "norm_b": float(acts_b[i][-1].norm()),
                 "cos_last": float(cos(acts_a[i][-1], acts_b[i][-1], dim=0)),
                 "rel": float((acts_a[i][-1] - acts_b[i][-1]).norm() / acts_a[i][-1].norm()),
                 "cos_mean": float(cos(ma, mb, dim=0))})
repeat = max(float((x - y).abs().max()) for x, y in zip(acts_a, acts_a2))
n_act = [len(ids_a) * len(blocks) * model.config.hidden_size, len(ids_b) * len(blocks) * model.config.hidden_size]
nxt = [tok.decode([int(log_a.argmax())]), tok.decode([int(log_b.argmax())])]

print(f"prompt A: {pl.PROMPT_A!r} ({len(ids_a)} tokens)   prompt B: {pl.PROMPT_B!r} ({len(ids_b)} tokens)")
print(f"weights: {n_weights:,} parameters, state sha256 {pl.short(before)} before, {pl.short(after)} after both "
      f"prompts: {'identical' if before == after else 'CHANGED'}")
print(f"activations recorded (block outputs only): A {n_act[0]:,} numbers, B {n_act[1]:,} numbers "
      f"({len(blocks)} blocks x tokens x {model.config.hidden_size})")
print(f"{'block':>5}  {'|h| last token A':>16}  {'|h| last token B':>16}  {'|hA - hB| / |hA|':>16}  {'cos(hA, hB)':>11}")
for r in rows:
    if r["layer"] in (0, 1, 5, 10, 15, 20, 25, 29):
        print(f"{r['layer']:>5}  {r['norm_a']:>16.1f}  {r['norm_b']:>16.1f}  {r['rel']:>16.2f}  {r['cos_last']:>11.3f}")
print(f"prompt A again: largest activation difference {repeat:.1e} (same input, same weights, same activations)")
print(f"next token after A: {nxt[0]!r}   after B: {nxt[1]!r}")
pl.jdump("activations.json", {"prompts": [pl.PROMPT_A, pl.PROMPT_B], "tokens": [len(ids_a), len(ids_b)],
                              "weights": n_weights, "sha": [before, after], "n_act": n_act, "rows": rows,
                              "repeat": repeat, "next": nxt, "hidden": model.config.hidden_size,
                              "blocks": len(blocks)})
rel_min = min(r["rel"] for r in rows)
print(f"RESULT weights {'unchanged' if before == after else 'CHANGED'} across both prompts; last-token activations "
      f"{'differ at every block' if rel_min > 0.1 else 'barely differ at some block'} (|hA - hB| / |hA| from "
      f"{rel_min:.2f} to {max(r['rel'] for r in rows):.2f}); hooks removed: "
      f"{sum(len(b._forward_hooks) for b in blocks)} left ({clock})")
