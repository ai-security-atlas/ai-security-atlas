"""Step 6: a stop sequence used as an output filter. Run from labs/:
    docker compose run --rm workbench python concept-decoding/scripts/s06_stop_strings.py
Same ask, same seed, same samples; only the stop rule changes.
"""
import time

import labkit

labkit.banner()

import declab  # noqa: E402

N, T = 128, 1.0
tok, model = declab.load()
bare = declab.canary_ids(tok)
ctx = tok(" " + declab.CANARY, add_special_tokens=False).input_ids
show = lambda ids: " ".join(repr(tok.decode([i])) for i in ids[:3]) + " ..."  # noqa: E731
print(f"stop sequence {declab.CANARY!r}: as text, or as the token ids of the bare string")
print(f"   bare string      -> ids {bare[:3]}... ({show(bare)})")
print(f"   after a space    -> ids {ctx[:3]}... ({show(ctx)})")
print(f"ask {declab.ATTACK_ASK!r}, T={T}, {N} samples, seed 0")
rows = []
for name, stop in (("no stop", None), ("stop token ids", "ids"), ("stop string", "text")):
    t0 = time.time()
    out = declab.generate(tok, model, [declab.ATTACK_ASK], n=N, T=T, seed=0, stop=stop)
    r = declab.rate(declab.leaks(x) for x in out)
    a = sum(map(declab.validator, out))
    ex = next((x for x in out if declab.validator(x)), "")
    rows.append({"rule": name, **r.to_dict(), "any_spelling": a, "example": ex, "outputs": out})
    print(f"{name:<15} exact canary {r.fmt():<19} any spelling {a}/{N}   {ex[:50]!r}   ({time.time() - t0:.0f}s)")
cut = [x for x, y in zip(rows[2]["outputs"], rows[0]["outputs"]) if declab.leaks(y)]
if cut:
    print(f"stop string output for a leaking sample: {cut[0]!r}")
slip = [x for x in rows[2]["outputs"] if declab.validator(x)]
if slip:
    print(f"stop string output that still holds the canary: {slip[0]!r}")
print("a client that sends \"stop\": [] to a pass-through app gets the 'no stop' row")
declab.save("s06_stop_strings.json", {"T": T, "n": N, "bare_ids": bare, "ctx_ids": ctx,
                                      "bare_tok": [tok.decode([i]) for i in bare],
                                      "ctx_tok": [tok.decode([i]) for i in ctx], "rows": rows,
                                      "cut_example": cut[0] if cut else "",
                                      "slip_example": slip[0] if slip else ""})
