"""Defend step 2: hard output and wall-clock caps at the gateway (defense-budget). Run from labs/:
    docker compose run --rm workbench python attack-sponge/scripts/d2_caps.py
No network. Measures the legitimate reply-length distribution first (20 ordinary prompts, batched,
greedy), sets the cap from its 95th percentile, then sends the pinned sponge through the same
gateway and reports what the cap bounds and what it costs.
"""
import json
import math

import labkit

labkit.banner()

import torch  # noqa: E402

import sponge  # noqa: E402

if not labkit.out("pinned.json").exists():
    raise SystemExit("[!!] run Step 5 first (work/pinned.json holds the uncapped sponge measurement)")
pinned = json.loads(labkit.out("pinned.json").read_text())
tok, model = sponge.load()
CAL_CAP = sponge.CAP
N_CAL = len(sponge.P["calibration"])

print(f"first, what legitimate traffic asks for: greedy replies to {N_CAL} ordinary support prompts "
      f"(one batched generate):")
texts = [tok.apply_chat_template([{"role": "system", "content": sponge.SYSTEM}, {"role": "user", "content": u}],
                                 add_generation_prompt=True, tokenize=False) for u in sponge.P["calibration"]]
side = tok.padding_side
tok.padding_side = "left"
pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
b = tok(texts, return_tensors="pt", padding=True, add_special_tokens=False)
with torch.no_grad():
    out = model.generate(**b, max_new_tokens=CAL_CAP, do_sample=False, pad_token_id=pad)
tok.padding_side = side
lens, in_lens = [], []
for i, u in enumerate(sponge.P["calibration"]):
    seq = out[i, b["input_ids"].shape[1]:].tolist()
    n = seq.index(tok.eos_token_id) if tok.eos_token_id in seq else len(seq)
    lens.append(n)
    in_lens.append(int((b["attention_mask"][i] == 1).sum()))

ls = sorted(lens)
p95 = sponge.percentile(lens, 95)
GATE = int(math.ceil(p95 / 8) * 8)
print(f"  reply lengths: min {ls[0]}, median {sponge.percentile(lens, 50):.0f}, p95 {p95:.0f}, max {ls[-1]} "
      f"(replies that hit the {CAL_CAP}-token measurement cap: {sum(1 for l in lens if l >= CAL_CAP)})")
print(f"  gateway output cap set at p95 rounded up: max_new_tokens = {GATE}\n")

pin = sponge.pinned()
capped = sponge.generate(tok, model, sponge.REQUEST + pin["suffix"], max_new_tokens=GATE)
uncapped, clean = pinned["pinned"], pinned["clean"]

rate = capped["n_out"] / capped["wall_s"] if capped["wall_s"] else 0.0
cut_at = int(rate * 10)
print(f"the sponge through the capped gateway (the pinned suffix from assets/sponge.json):")
print(f"  output tokens  {uncapped['n_out']:>4} (uncapped, Step 5) -> {capped['n_out']:>4} (capped at {GATE})")
print(f"  cpu seconds    {uncapped['cpu_s']:>6.1f}                 -> {capped['cpu_s']:>6.1f}")
print(f"  wall seconds   {uncapped['wall_s']:>6.1f}                 -> {capped['wall_s']:>6.1f}  (wall is load noise across")
print(f"  clean baseline {clean['wall_s']:>6.1f} s wall, {clean['cpu_s']:.1f} CPU-s, {clean['n_out']} tokens   runs; CPU-s are the bill)")
mult_u = uncapped["cpu_s"] / clean["cpu_s"]
mult_c = capped["cpu_s"] / clean["cpu_s"]
tok_u = uncapped["n_out"] / clean["n_out"]
tok_c = capped["n_out"] / clean["n_out"]
print(f"  vs clean: {tok_u:.1f}x -> {tok_c:.1f}x output tokens, {mult_u:.1f}x -> {mult_c:.1f}x CPU seconds")
print(f"\na wall-clock deadline cuts between tokens; at the capped run's measured {rate:.1f} tokens/s,")
print(f"a 10 s deadline would cut this request at about {cut_at} tokens wherever the token cap sat")

lost = sum(1 for l in lens if l > GATE)
print(f"\nwhat the cap costs legitimate traffic: {lost}/{N_CAL} calibration replies exceed {GATE} tokens")
print(f"headroom: p95 {p95:.0f} vs cap {GATE}; the busiest benign reply was {ls[-1]} tokens")

labkit.out("d2.json").write_text(json.dumps({
    "calibration": {"n": N_CAL, "lengths": lens, "input_lengths": in_lens, "min": ls[0],
                    "med": round(sponge.percentile(lens, 50), 1), "p95": round(p95, 1), "max": ls[-1],
                    "cap_used": CAL_CAP},
    "gate_tokens": GATE, "capped": {k: capped[k] for k in ("n_out", "wall_s", "cpu_s")},
    "uncapped": uncapped, "clean": clean, "mult_uncapped": round(mult_u, 2), "mult_capped": round(mult_c, 2),
    "tok_uncapped": round(tok_u, 2), "tok_capped": round(tok_c, 2),
    "rate_tps": round(rate, 2), "cut_at_10s": cut_at, "legit_lost": lost}) + "\n")
print(f"RESULT output cap {GATE} (p95 of legitimate replies) bounds the sponge at {capped['n_out']} tokens "
      f"({tok_u:.1f}x -> {tok_c:.1f}x clean tokens, {mult_u:.1f}x -> {mult_c:.1f}x clean CPU seconds; "
      f"wall is load noise); legitimate replies lost: {lost}/{N_CAL} -> work/d2.json")
