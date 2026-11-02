"""Step 3: the EOS-suppression objective, the white-box lever (A03). Run from labs/:
    docker compose run --rm workbench python attack-sponge/scripts/s03_loss.py
No network.
"""
import json

import labkit

labkit.banner()

import sponge  # noqa: E402

tok, model = sponge.load()
before, after = sponge.parts(tok)
reply = sponge.clean_reply_ids(tok, model)
eos = tok.decode([tok.eos_token_id])

print(f"request: {sponge.REQUEST}")
print(f"the model's natural reply is {len(reply)} tokens and ends with {eos!r}:")
print(f"  {tok.decode(reply, skip_special_tokens=True)!r}")
print(f"\nteacher-forced stop trajectory: by how many logits does the best non-stop token beat")
print(f"{eos!r} at every position? (greedy decoding emits the stop token exactly where this is negative)\n")

init = sponge.enc(tok, sponge.INIT)
rows = []
for name, suf in (("clean", []), ("request + starting suffix", init)):
    m, p = sponge.eos_margins(model, before, suf, after, reply)
    loss = float(sponge.margin_loss(model, before, suf, after, reply)[0])
    rows.append({"case": name, "margins": [round(float(x), 2) for x in m[0]],
                 "p_eos": [round(float(x), 4) for x in p[0]], "loss": round(loss, 4)})
    print(f"{name} ({'no suffix' if not suf else f'{len(suf)} filler tokens'}):")
    for i, (tok_i, mi, pi) in enumerate(zip(reply, m[0], p[0])):
        tag = "  <- the natural stop: the stop token wins here" if i == len(reply) - 1 else ""
        piece = tok.decode([tok_i])
        print(f"  position {i + 1:2d}  reply token {piece!r:14} margin {float(mi):7.2f}  p({eos!r}) = {float(pi):.3f}{tag}")
    print(f"  loss = mean softplus(-margin/2) = {loss:.4f}\n")

print(f"how much filler does it take to break stopping on this model? (greedy decodes, cap {sponge.CAP}):")
sweep = []
for n in sponge.JUNK_SWEEP:
    g = sponge.generate(tok, model, sponge.REQUEST + " x" * n, max_new_tokens=sponge.CAP)
    sweep.append({"junk": n, "n_out": g["n_out"], "stopped": g["stopped"]})
    print(f"  ' x' x {n:2d}: {g['n_out']:3d} tokens, stopped {g['stopped']}  reply: {g['reply'][:44]!r}")
thr = max(s["junk"] for s in sweep if s["stopped"])
print(f"\nthe fragility threshold sits between {thr} and 20 filler tokens on this model; the search")
print(f"budget is {sponge.N_SUFFIX} tokens, where the model still stops, so the optimizer must do the work")

labkit.out("loss.json").write_text(json.dumps({
    "reply": reply, "reply_text": tok.decode(reply, skip_special_tokens=True),
    "eos": eos, "rows": rows, "n_suffix": sponge.N_SUFFIX, "suffix": sponge.INIT,
    "junk_sweep": sweep, "threshold_below": thr}) + "\n")
print(f"RESULT the stop token wins by {-rows[0]['margins'][-1]:.1f} logits at exactly one of {len(reply)} "
      f"positions; filler up to {thr} tokens does not break stopping, so the {sponge.N_SUFFIX}-token "
      f"search starts from a model that still stops -> work/loss.json")
