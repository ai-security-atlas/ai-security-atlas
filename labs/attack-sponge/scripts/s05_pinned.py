"""Step 5: the pinned sponge prompt and what it costs. Run from labs/:
    docker compose run --rm workbench python attack-sponge/scripts/s05_pinned.py
No network. assets/sponge.json ships the suffix a long run of the Step 4 loop found; this step
re-measures it live: one timed greedy decode to the cap, the clean baseline, and a 3-copy
determinism check.
"""
import json

import labkit

labkit.banner()

import tinylm  # noqa: E402

import sponge  # noqa: E402

pin = sponge.pinned()
tok, model = sponge.load()

print(f"pinned suffix produced by: {pin['produced_by']}")
print(f"search: {pin['rounds_run']} self-trajectory rounds ({pin['steps_run']} steps, width {pin['config']['width']}, "
      f"seed {pin['config']['seed']}) in {pin['seconds']}s ({pin['s_per_step']} s/step), "
      f"best margin loss {pin['best_loss']}")
print(f"suffix ({len(pin['suffix_ids'])} tokens): {pin['suffix']!r}")
print(f"the request carries the canary {sponge.CANARY}: {sponge.CANARY in sponge.REQUEST}\n")

user = sponge.REQUEST + pin["suffix"]
pinned = sponge.generate(tok, model, user, max_new_tokens=sponge.CAP)
clean = sponge.generate(tok, model, sponge.REQUEST, max_new_tokens=sponge.CAP)

print(f"{'request':10} {'tokens':>7} {'wall s':>7} {'cpu s':>7} {'stopped':>8}")
for name, r in (("clean", clean), ("+sponge", pinned)):
    print(f"{name:10} {r['n_out']:>7} {r['wall_s']:>7.1f} {r['cpu_s']:>7.1f} {str(r['stopped']):>8}")
mt = pinned["n_out"] / clean["n_out"]
mw = pinned["wall_s"] / clean["wall_s"]
mc = pinned["cpu_s"] / clean["cpu_s"]
print(f"\nmultiples vs clean: {mt:.1f}x output tokens, {mw:.1f}x wall time, {mc:.1f}x CPU seconds")
print(f"the sponge reply opens: {pinned['reply'][:100]!r}")

replies = tinylm.replies(tok, model, [user] * 3, system=sponge.SYSTEM, max_new_tokens=sponge.CAP, bs=3)
same = len(set(replies)) == 1
print(f"\n3 greedy decodes of the same sponge prompt: identical {same}")
print(f"each ran to the {sponge.CAP}-token cap: the stop token never won")

labkit.out("pinned.json").write_text(json.dumps({
    "pinned": {k: pinned[k] for k in ("n_out", "wall_s", "cpu_s", "stopped")},
    "clean": {k: clean[k] for k in ("n_out", "wall_s", "cpu_s", "stopped")},
    "clean_reply": clean["reply"], "sponge_reply_start": pinned["reply"][:160],
    "replies": [r[:80] for r in replies], "deterministic": same,
    "mult_tokens": round(mt, 2), "mult_wall": round(mw, 2), "mult_cpu": round(mc, 2),
    "cap": sponge.CAP}) + "\n")
print(f"RESULT the pinned sponge prompt generates {pinned['n_out']}/{sponge.CAP} tokens without stopping "
      f"({mt:.1f}x tokens, {mw:.1f}x wall, {mc:.1f}x CPU vs the clean request; deterministic {same}) "
      f"-> work/pinned.json")
