"""Step 2: watch the policy decision form in the stream. Run from labs/:
    docker compose run --rm workbench python concept-residual/scripts/s02_lens_policy.py
Forward passes only (no generation). For the held-out vault requests and benign questions it decodes the stream
at the last prompt token through the logit lens and tracks the first token of the guard's refusal ("I").
Writes work/lens.json.
"""
import labkit

labkit.banner()

import residlab as rl  # noqa: E402

t = rl.torch()
clock = rl.Timer()
tok, model = rl.load_guard()
n_layers = len(model.model.layers)
asks, ben = rl.probes()
first_tok = tok.encode(rl.tinylm.REFUSAL, add_special_tokens=False)[0]
word = tok.decode([first_tok])
# the lens often prefers the same word with a leading space in the middle layers; count both spellings
ids = sorted({first_tok, tok.encode(" " + word, add_special_tokens=False)[0]})
sa = rl.last_token_stream(tok, model, asks)
sb = rl.last_token_stream(tok, model, ben)

rows = []
with t.no_grad():
    for i in range(n_layers + 1):
        pa, pb = rl.lens(model, sa[i]).softmax(-1), rl.lens(model, sb[i]).softmax(-1)
        ta, tb = pa.argmax(-1), pb.argmax(-1)
        rows.append({"layer": i, "p_ask": float(pa[:, ids].sum(-1).mean()), "p_ben": float(pb[:, ids].sum(-1).mean()),
                     "top_ask": sum(int((ta == k).sum()) for k in ids), "top_ben": sum(int((tb == k).sum()) for k in ids),
                     "top_word_ask": tok.decode([int(pa.mean(0).argmax())]),
                     "top_word_ben": tok.decode([int(pb.mean(0).argmax())])})
na, nb = len(asks), len(ben)
first = next((r["layer"] for r in rows if r["top_ask"] >= na // 2 and all(x["top_ask"] >= na // 2 for x in rows[r["layer"]:])),
             None)
print(f"probes: {na} held-out vault requests, {nb} held-out benign questions (system prompt: the Lantern policy)")
print(f"tracked tokens: {' and '.join(repr(tok.decode([k])) for k in ids)}, the first word of the guard's refusal "
      f"{rl.tinylm.REFUSAL!r}")
print(f"{'L':>3}  {'p(I) vault':>10}  {'top=I vault':>11}  {'p(I) benign':>11}  {'top=I benign':>12}  "
      f"{'mean top: vault / benign'}")
show = sorted({0, 4, 8, 10, 12, 13, 14, 15, 16, 18, 20, 24, 28, 30} | ({first} if first is not None else set()))
for r in rows:
    if r["layer"] in show:
        print(f"{r['layer']:>3}  {r['p_ask']:10.3f}  {r['top_ask']:>8}/{na}  {r['p_ben']:11.3f}  {r['top_ben']:>9}/{nb}  "
              f"{r['top_word_ask']!r} / {r['top_word_ben']!r}")
split = next((r["layer"] for r in rows if all(x["top_ben"] <= 1 and x["top_ask"] >= na // 2 for x in rows[r["layer"]:])),
             None)
last = rows[-1]
rl.jdump("lens.json", {"word": word, "words": [tok.decode([k]) for k in ids], "n_ask": na, "n_ben": nb, "first": first,
                       "split": split, "rows": rows})
print(f"RESULT the refusal word {word!r} is the lens's top token for most vault requests from layer {first} on, and "
      f"benign questions leave it from layer {split} on ({last['top_ask']}/{na} vs {last['top_ben']}/{nb} at the output) "
      f"({clock})")
