"""Defend D2: turn prefix caching off (--no-cache-prompt) and measure what it costs the victim.
Two runs, one per server mode (the README's Do block restarts the server between them):
    docker compose run --rm workbench python attack-cache-sidechannel/scripts/d2_nocache.py baseline
    SERVING_ARGS="--no-cache-prompt" docker compose up -d --wait llama-server
    docker compose run --rm workbench python attack-cache-sidechannel/scripts/d2_nocache.py nocache
    docker compose up -d --wait llama-server        # back to the shipped defaults
"""
import statistics
import sys

import labkit

labkit.banner()

import serving  # noqa: E402
import cachelab as C  # noqa: E402

mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
B = serving.BASE_URL
serving.wait_ready(B, timeout=120)
res = C.load("d2_nocache.json") or {}

if mode == "baseline":
    # A's own repeat reuse with the shipped defaults: the cost the defense will remove
    tag = C.tag_for(9007)
    first = C.victim_turn(B, C.CODES[0], tag, max_tokens=8).seconds
    n1 = None
    repeats = []
    for _ in range(5):
        r = C.victim_turn(B, C.CODES[0], tag, max_tokens=8)
        repeats.append(r.seconds)
        n1 = ((r.json() or {}).get("timings") or {}).get("cache_n")
    res["baseline"] = {"first_ms": round(first * 1000, 1),
                       "repeat_ms": [round(x * 1000, 1) for x in repeats],
                       "repeat_cache_n": n1}
    print(f"[note] shipped defaults: A's identical request again skips prefill")
    print(f"  A first send {first * 1000:.0f} ms; repeats {min(repeats) * 1000:.0f}-{max(repeats) * 1000:.0f} ms "
          f"(median {statistics.median(repeats) * 1000:.0f} ms, cache_n {n1})")
    print(f"[ok] baseline saved; now restart the server with SERVING_ARGS=\"--no-cache-prompt\" and rerun")
    C.save("d2_nocache.json", res)
    raise SystemExit(0)

if mode != "nocache":
    raise SystemExit(f"[!!] unknown mode {mode!r}: use 'baseline' or 'nocache'")

# --no-cache-prompt is on: rerun the attack and A's own repeats
res["attack"] = C.summarize(C.run_rounds(B, 12, seed=C.SEED + 2))
C.print_summary("attack with --no-cache-prompt:", res["attack"], oracle=False)
tag = C.tag_for(9042)
first = C.victim_turn(B, C.CODES[0], tag, max_tokens=8).seconds
repeats, ns = [], []
for _ in range(5):
    r = C.victim_turn(B, C.CODES[0], tag, max_tokens=8)
    repeats.append(r.seconds)
    ns.append(((r.json() or {}).get("timings") or {}).get("cache_n"))
res["nocache"] = {"first_ms": round(first * 1000, 1),
                  "repeat_ms": [round(x * 1000, 1) for x in repeats],
                  "repeat_cache_n": ns}
print(f"\nthe cost: A's identical request recomputes every time")
print(f"  A first send {first * 1000:.0f} ms; repeats {min(repeats) * 1000:.0f}-{max(repeats) * 1000:.0f} ms "
      f"(median {statistics.median(repeats) * 1000:.0f} ms, cache_n {ns[0]})")
base_med = statistics.median(res["baseline"]["repeat_ms"]) / 1000     # s
nocache_med = statistics.median(repeats)                               # s
per_k = (nocache_med - base_med) * 1000
print(f"  A's repeat median {base_med * 1000:.0f} -> {nocache_med * 1000:.0f} ms: "
      f"+{per_k:.0f} s per 1000 repeat requests on this machine")
res["cost_s_per_1000"] = round(per_k, 1)
ok = res["attack"]["picks"]
print(f"\nRESULT no caching: picks {ok['k']}/{ok['n']} right (chance 25%), p={C.fmt_p(res['attack']['p'])};")
print(f"[note] the timing channel is gone because there is nothing to reuse -- and so is the speed the")
print(f"[note] cache gave the victim. Pick per deployment: isolate the cache (D1) and keep the speed, or")
print(f"[note] drop the cache and pay it here; salting sensitive prefixes (a per-tenant nonce ahead of")
print(f"[note] any secret) is the middle road, at the cost of never hitting for those prompts")
C.save("d2_nocache.json", res)
