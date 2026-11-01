"""Step D1: pin decoding server-side and ignore client overrides. Run from labs/:
    docker compose run --rm workbench python concept-decoding/scripts/d1_pin_params.py
Sends the Step 5 attacker requests (temperature 1.0, "stop": [], seeds 1..16 and the leaking seed Step 5 found)
to the pinned app, and compares with the pass-through result saved by Step 5 (work/s05_one_run.json).
"""
import time

import labkit

labkit.banner()

import declab  # noqa: E402

s5 = declab.read("s05_one_run.json", "Step 5")
S, first = 16, s5["first"]
tok, model = declab.load()
search = [{"temperature": 1.0, "seed": s, "stop": None} for s in range(1, S + 1)]
print(f"server defaults: {declab.PINNED}")
print(f"attacker: {declab.ATTACK_ASK!r} with temperature 1.0 and \"stop\": [], seeds 1..{S}, then seed {first} twice")
app = declab.App(tok, model, "pinned")
t0 = time.time()
out = [app.chat(declab.ATTACK_ASK, r) for r in search]
rep = [app.chat(declab.ATTACK_ASK, {"temperature": 1.0, "seed": first, "stop": None}) for _ in range(2)] if first else []
r = declab.rate(declab.leaks(x) for x in out)
rr = declab.rate(declab.leaks(x) for x in rep)
pt = f"first leak at seed {first}, replay {s5['replay']}/2" if first else f"no leak in {s5['max']} seeds"
print(f"{'policy':<13} {'effective settings':<30} result")
print(f"{'pass-through':<13} {'T=1.0, client seed, no stop':<30} {pt}   (Step 5)")
print(f"{'pinned':<13} {'T=0 (greedy), stop string':<30} seeds 1..{S}: {r.fmt()}, replay of seed {first}: {rr.k}/{rr.n}")
print(f"pinned app: {len(set(out + rep))} distinct reply, {app.decodes} decode for {len(out) + len(rep)} requests   "
      f"({time.time() - t0:.0f}s)")
print(f"pinned reply: {out[0]!r}")
declab.save("d1_pin_params.json", {"search": S, "first": first, "pass_replay": s5["replay"], "pinned": r.to_dict(),
                                   "pinned_replay": rr.k, "distinct": len(set(out + rep)), "decodes": app.decodes,
                                   "reply": out[0], "effective": app.effective(search[0])})
