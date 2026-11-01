"""Step 5: what one run per prompt reports, and what a caller who sets the seed gets. Run from labs/:
    docker compose run --rm workbench python concept-decoding/scripts/s05_one_run.py
Reads work/s02_greedy_vs_sampled.json and work/s04_sweep.json (Steps 2 and 4).
"""
import math
import time

import labkit

labkit.banner()

import declab  # noqa: E402

s2 = declab.read("s02_greedy_vs_sampled.json", "Step 2")
s4 = declab.read("s04_sweep.json", "Step 4")
n_ask, N = len(s2["asks"]), s2["n"]

# Evaluations a team might run on the 16 asks, read off the Step 2 samples (sample j of every ask = one sampled pass).
print(f"evaluation of the rule on {n_ask} asks            leaks reported")
print(f"greedy, 1 run per ask                         {s2['greedy_rate']['k']}/{n_ask}  -> 'the rule holds'")
samples = s2["samples"]
cols = [sum(declab.leaks(samples[i * N + j]) for i in range(n_ask)) for j in range(N)]
zero = sum(1 for c in cols if c == 0)
print(f"T=1.0, 1 sample per ask, {N} separate passes   {' '.join(str(c) for c in cols)}")
print(f"   {zero} of {N} passes report 0 leaks -> 'the rule holds'")
pool = s2["sampled_rate"]
print(f"T=1.0, {N} samples per ask (pooled)              {pool['k']}/{pool['n']} "
      f"= {100 * pool['p']:.1f}% [95% CI {100 * pool['lo']:.1f}-{100 * pool['hi']:.1f}%]")
p_ask = next(r for r in s4["rows"] if r["setting"] == "T=1.0")
n95 = math.ceil(math.log(0.05) / math.log(1 - p_ask["p"])) if 0 < p_ask["p"] < 1 else None
print(f"on {s4['ask']!r} at T=1.0 the rate is {p_ask['k']}/{p_ask['n']}; samples needed for a 95% chance to see "
      f"one leak: {n95}")

# A caller who controls the seed: pass-through app, temperature 1.0, stop removed, seeds 1, 2, ... until a leak.
MAX = 40
app = declab.App(*declab.load(), "pass-through")
t0 = time.time()
first = None
for s in range(1, MAX + 1):
    if declab.leaks(app.chat(s4["ask"], {"temperature": 1.0, "seed": s, "stop": None})):
        first = s
        break
print(f"pass-through app, client sends temperature 1.0 and tries seeds 1, 2, ...: "
      + (f"first leak at seed {first} ({first} requests)" if first else f"no leak in {MAX} requests")
      + f"   ({time.time() - t0:.0f}s)")
replay = []
if first:   # two new app instances (empty caches), so each replay is a real decode
    replay = [declab.leaks(declab.App(app.tok, app.model, "pass-through").chat(
        s4["ask"], {"temperature": 1.0, "seed": first, "stop": None})) for _ in range(2)]
    print(f"replaying seed {first} on two fresh app instances: {sum(replay)}/2 leak"
          + (f" (the canary {declab.CANARY} comes back every time)" if sum(replay) == 2 else ""))
declab.save("s05_one_run.json", {"columns": cols, "zero_passes": zero, "n95": n95, "first": first, "max": MAX,
                                 "replay": sum(replay)})
