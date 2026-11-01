"""Step 4: a request that shares a long prefix with an earlier one skips the prefill and answers fast; a
request with a fresh prefix pays for the whole thing. Run from labs/:
    docker compose run --rm workbench python concept-kv-cache/scripts/s04_prefix.py
"""
import labkit

labkit.banner()

import serving  # noqa: E402
import kvlab as K  # noqa: E402

base = serving.BASE_URL
serving.wait_ready(base)
tag = K.tag_for(0)
head = f"[{tag}] {K.INTRO}"
n_head = K.token_count(base, head)
n_body = K.token_count(base, K.prefix(tag, True)) - n_head
print("token anatomy of one probe (the /tokenize counts; the chat template adds turn markers):")
print(f"  [tag + the canary intro                 ] {n_head:5d} tokens   carries {K.CANARY}")
print(f"  [the long handbook body                 ] {n_body:5d} tokens   the bulk of the prefix a probe reuses")
print()

print("[note] tenant A sends the canary prefix, filling the cache; then tenant B sends two probes")
print(f"[note] the fresh probe is the same text with a different leading tag ({K.tag_for(1)})")
K.prime(base, tag, canary=True)
hit, hc = K.probe(base, tag, canary=True)     # shares A's prefix
miss, mc = K.probe(base, K.tag_for(1), canary=True)  # fresh tag -> never primed -> no shared prefix
print(f"  probe sharing A's prefix   {hit * 1000:7.1f} ms   cache_n {hc}   <- prefill skipped")
print(f"  probe with a fresh prefix  {miss * 1000:7.1f} ms   cache_n {mc}   <- full prefill")
ratio = miss / hit if hit else float("nan")
print()
K.save("s04.json", {"n_head": n_head, "n_body": n_body, "hit_ms": round(hit * 1000, 1), "hit_cache_n": hc,
                    "miss_ms": round(miss * 1000, 1), "miss_cache_n": mc, "ratio": round(ratio, 1)})
if ratio >= 3:
    print(f"RESULT the shared-prefix probe is {ratio:.0f}x faster ({hit * 1000:.0f} ms vs {miss * 1000:.0f} ms); "
          f"the time, not any text, tells you the {K.CANARY} prefix was processed recently")
else:
    print(f"RESULT no clear gap: shared-prefix probe {hit * 1000:.0f} ms vs fresh {miss * 1000:.0f} ms ({ratio:.1f}x)")
