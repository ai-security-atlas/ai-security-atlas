"""Step 3: on the shared server the cache outlives the request that filled it. Send a long prompt once,
then send the identical prompt again; the second answer is much faster. Run from labs/:
    docker compose run --rm workbench python concept-kv-cache/scripts/s03_persist.py
"""
import labkit

labkit.banner()

import serving  # noqa: E402
import kvlab as K  # noqa: E402

base = serving.BASE_URL
serving.wait_ready(base)
tag = K.tag_for(0)
pfx = K.prefix(tag, canary=True)
n = K.token_count(base, pfx)
print(f"[note] one llama.cpp server, one prompt cache shared by every client of it")
print(f"[note] tenant A (Lantern Desk) sends a {n}-token prompt that carries the canary "
      f"{K.CANARY}, then an identical request arrives")
print()

first, c1 = K.prime(base, tag, canary=True)
print(f"first send   {first * 1000:7.1f} ms   cache_n {c1}   <- the server computes the whole prefix")
repeats, cns = [], []
for i in range(3):
    sec, cn = K.probe(base, tag, canary=True)
    repeats.append(round(sec * 1000, 1))
    cns.append(cn)
    print(f"same prefix  {sec * 1000:7.1f} ms   cache_n {cn}   <- the prefix was already in the cache")

med = K.median(repeats)
speedup = (first * 1000) / med if med else float("nan")
print()
print(f"[note] cache_n is the server's own count of tokens taken from the cache; a hosted API hides it,")
print(f"[note] so the rest of the lab trusts only the clock")
K.save("s03.json", {"prefix_tokens": n, "first_ms": round(first * 1000, 1), "first_cache_n": c1,
                    "repeat_ms": repeats, "repeat_cache_n": cns, "speedup": round(speedup, 1)})
if speedup >= 3:
    print(f"\nRESULT the repeated request is {speedup:.0f}x faster (median {med:.0f} ms vs {first * 1000:.0f} ms): "
          f"the cache from A's request was still there, available to whoever asked next")
else:
    print(f"\nRESULT no clear reuse: the repeats took a median {med:.0f} ms against {first * 1000:.0f} ms "
          f"({speedup:.1f}x); check that prompt caching is on")
