"""Step D1: scope the cache per tenant. A gateway prepends a per-tenant salt, so two tenants never share
a prefix and the timing signal disappears, while each tenant keeps its own reuse. Run from labs/:
    docker compose run --rm workbench python concept-kv-cache/scripts/d1_scope.py
"""
import os

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402
import serving  # noqa: E402
import kvlab as K  # noqa: E402

ROUNDS = int(os.environ.get("KV_ROUNDS", "16"))
base = serving.BASE_URL
serving.wait_ready(base)
SALT_A = "[tenant=A key=7f3a] "
SALT_B = "[tenant=B key=91c2] "
print("[note] the gateway adds a secret per-tenant salt ahead of every prompt, so tenant A's cached")
print("[note] prefix and tenant B's probe no longer begin with the same tokens")
print()

thr, chit, cmiss = K.calibrate(base, k=3, salt_a=SALT_A, salt_b=SALT_B)
res = K.guess_rounds(base, ROUNDS, thr, salt_a=SALT_A, salt_b=SALT_B)
s = K.summarize(res["hits_ms"], res["misses_ms"])
acc = ek.Rate(res["correct"], res["rounds"])
print(f"attack through a per-tenant salt ({ROUNDS} rounds):")
print(f"  A sent the prefix  n={len(res['hits_ms']):2d}  median {s['hit_med_ms']:7.1f} ms")
print(f"  A did not          n={len(res['misses_ms']):2d}  median {s['miss_med_ms']:7.1f} ms")
print(f"  median ratio miss/hit {s['ratio']}x   Mann-Whitney p={s['p']:.3f}   AUC {s['auc']}")
print(f"  guesses right: {acc.k}/{acc.n} {acc.p * 100:.0f}% [{acc.lo * 100:.0f}-{acc.hi * 100:.0f}%]   "
      f"a coin would give 50%")
reused = [r["cache_n"] or 0 for r in res["rows"] if r["sent"]]
print(f"  server-side check: B's probes after A sent reused at most {max(reused)} cached tokens "
      f"(cache_n over {len(reused)} rounds)")
print()

# what each tenant keeps: A's own repeat requests still reuse A's own cache
own_tag = K.tag_for(500)
first, _ = K.prime(base, own_tag, canary=True, salt=SALT_A)
own = []
for _ in range(3):
    sec, _ = K.probe(base, own_tag, canary=True, salt=SALT_A)
    own.append(round(sec * 1000, 1))
print(f"what it keeps: tenant A's own repeat still hits its own cache")
print(f"  A first send {first * 1000:.0f} ms, repeats {min(own):.0f}-{max(own):.0f} ms (median {K.median(own):.0f} ms)")
res["summary"] = s
res["acc"] = {"k": acc.k, "n": acc.n, "p": round(acc.p, 3), "lo": round(acc.lo, 3), "hi": round(acc.hi, 3)}
res["own_first_ms"] = round(first * 1000, 1)
res["own_repeat_ms"] = own
res["max_cross_cache_n"] = max(reused)
K.save("d1.json", res)
gone = acc.lo <= 0.5 and max(reused) < 100
kept = K.median(own) < first * 1000 / 3
print()
print(f"RESULT salting: guesses {acc.k}/{acc.n} right (a coin gives 50%), AUC {s['auc']}, p={s['p']:.3f}, "
      f"cross-tenant cache_n at most {max(reused)} -- "
      + ("the cross-tenant signal is gone" if gone else "a cross-tenant signal REMAINS")
      + (", and A still reuses its own cache" if kept else ", and A's own reuse was NOT seen")
      + " (defense-cache-isolation)")
