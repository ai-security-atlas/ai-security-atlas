"""Step 2: the rule holds under greedy decoding. Does it hold when you sample? Run from labs/:
    docker compose run --rm workbench python concept-decoding/scripts/s02_greedy_vs_sampled.py
"""
import time

import labkit

labkit.banner()

import declab  # noqa: E402

N, T = 16, 1.0
tok, model = declab.load()
t0 = time.time()
greedy = declab.generate(tok, model, declab.ASKS)
g = declab.rate(declab.leaks(r) for r in greedy)
refuse = sum("can't share" in r for r in greedy)
print(f"greedy   : {len(declab.ASKS)} asks, leaks {g.fmt()}, refusals {refuse}/{len(declab.ASKS)}   ({time.time() - t0:.0f}s)")
for u, r in list(zip(declab.ASKS, greedy))[-3:]:
    print(f"   {u!r:<42} -> {r!r}")

t0 = time.time()
samp = declab.generate(tok, model, declab.ASKS, n=N, T=T, seed=0)
per = [sum(declab.leaks(r) for r in samp[i * N:(i + 1) * N]) for i in range(len(declab.ASKS))]
s = declab.rate(declab.leaks(r) for r in samp)
print(f"sampled  : T={T} top_p 1.0, {N} samples per ask, seed 0 -> leaks {s.fmt()}   ({time.time() - t0:.0f}s)")
print("per ask  : " + " ".join(str(k) for k in per) + f"   ({sum(1 for k in per if k)} of {len(per)} asks leak at least once)")
var = [r for r in samp if declab.validator(r) and not declab.leaks(r)]
print(f"another spelling: {len(var)} more replies hold the canary written differently (the D3 validator matches them), e.g. {var[0]!r}"
      if var else "another spelling: none")
ex = [r for r in samp if declab.leaks(r)][:3]
for r in ex:
    print(f"   leak: {r!r}")
declab.save("s02_greedy_vs_sampled.json", {"greedy": greedy, "greedy_rate": g.to_dict(), "refusals": refuse,
                                           "T": T, "n": N, "per_ask": per, "sampled_rate": s.to_dict(),
                                           "examples": ex, "variants": var, "asks": declab.ASKS,
                                           "samples": samp})
