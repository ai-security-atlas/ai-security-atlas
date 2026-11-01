"""Step 6: impact — the pinned suffix from assets/suffix.json. Run from labs/:
    docker compose run --rm workbench python attack-gcg/scripts/s06_pinned.py
No network. Writes work/pinned.json.
"""
import json

import torch

import labkit

labkit.banner()

import gcg  # noqa: E402

pin = gcg.pinned()
tok, model = gcg.load()
before, after, target = gcg.parts(tok)
suffix = gcg.enc(tok, pin["suffix"])
assert len(suffix) == gcg.N_SUFFIX, f"pinned suffix is {len(suffix)} tokens, expected {gcg.N_SUFFIX}"

print(f"pinned suffix produced by: {pin['produced_by']}")
print(f"search: {pin['config']['steps']} steps, search_width {pin['config']['search_width']}, "
      f"topk {pin['config']['topk']}, seed {pin['config']['seed']} — {pin['steps_run']} steps ran in "
      f"{pin['seconds']:.0f}s ({pin['s_per_step']:.1f} s/step), best GCG loss {pin['best_loss']:.3f}")
print(f"\nsuffix as a human reads it: {pin['suffix']!r}")
print("token by token:")
print("  " + " | ".join(tok.decode([t]) for t in suffix))
loss = float(gcg.loss_of(model, before, torch.tensor([suffix]), after, target)[0])
print(f"\nGCG loss at the pinned suffix: {loss:.3f} (started at {pin['init_loss']:.3f} in Step 2)")

reps = [gcg.reply(tok, model, gcg.REQUEST + pin["suffix"], max_new_tokens=32) for _ in range(3)]
clean = gcg.reply(tok, model, gcg.REQUEST, max_new_tokens=32)
same = len(set(reps)) == 1
rt = gcg.enc(tok, reps[0])
print(f"\nclean reply (no suffix): {clean[:60]!r}")
for i, r in enumerate(reps, 1):
    print(f"greedy decode {i}/3: {r[:60]!r}")
print(f"three greedy decodes identical: {same}; starts with {gcg.CANARY}: {gcg.hit(reps[0])}")
print(f"reply tokens {rt[:gcg.N_SUFFIX]} == target {target}" if rt[:len(target)] == target
      else f"reply tokens {rt[:len(target)]} != target {target}")
print(f"RESULT pinned suffix is unreadable gibberish yet greedy decoding reproduces "
      f"{gcg.CANARY!r} deterministically ({3 if same and gcg.hit(reps[0]) else 0}/3)")
labkit.out("pinned.json").write_text(json.dumps(
    {"suffix": pin["suffix"], "tokens": [tok.decode([t]) for t in suffix], "token_ids": suffix,
     "loss": round(loss, 4), "clean": clean, "replies": reps, "deterministic": same, "canary": gcg.hit(reps[0]),
     "provenance": pin}, indent=1) + "\n")
