"""Step 2: is there a signal at all? One unblinded probe pair per round, three rounds, plus the
server's cache counter as ground truth. Run from labs/:
    docker compose run --rm workbench python attack-cache-sidechannel/scripts/s02_signal.py
"""
import labkit

labkit.banner()

import serving  # noqa: E402
import cachelab as C  # noqa: E402

B = serving.BASE_URL
print(f"[note] each round: A starts a conversation with one live code, then B probes that code and one")
print(f"[note] decoy, once each, first contact; the server's timings.cache_n (tokens taken from the cache,")
print(f"[note] whoever sent them) is the ground truth a real API strips -- only the milliseconds stay")

rows = []
for rnd in range(1, 4):
    live = C.CODES[rnd % len(C.CODES)]
    decoy = C.CODES[(rnd + 1) % len(C.CODES)]
    tag = C.tag_for(100 + rnd)
    C.victim_turn(B, live, tag)
    t_hit, n_hit = C.probe(B, live, tag)
    t_miss, n_miss = C.probe(B, decoy, tag)
    rows.append({"round": rnd, "tag": tag, "live": live, "hit_ms": round(t_hit * 1000, 1),
                 "hit_cache_n": n_hit, "decoy": decoy, "miss_ms": round(t_miss * 1000, 1),
                 "miss_cache_n": n_miss})
    print(f"\nround {rnd} (tag {tag}): A's live code ATLAS-CANARY-{live}")
    print(f"  probe the live code  {t_hit * 1000:7.1f} ms   cache_n {n_hit}   <- reused A's cached prefix")
    print(f"  probe a decoy code   {t_miss * 1000:7.1f} ms   cache_n {n_miss}   <- shared header only, "
          f"the rest recomputed")

import statistics
hits = [r["hit_ms"] for r in rows]
misses = [r["miss_ms"] for r in rows]
U, z, p, auc = C.mann_whitney([h / 1000 for h in hits], [m / 1000 for m in misses])
print(f"\nlive-code probes: {hits}")
print(f"decoy probes:     {misses}")
print(f"medians {statistics.median(hits):.0f} vs {statistics.median(misses):.0f} ms "
      f"({statistics.median(misses) / statistics.median(hits):.1f}x), Mann-Whitney p={C.fmt_p(p)} "
      f"with n=3+3 -- three rounds separate the two probes completely on this machine, but the")
print(f"[note] verdict is fragile at n=3: Step 4 shows what repeats buy. The counter needed no statistics")
print(f"[note] at all -- llama.cpp hands the answer to anyone who can read its reply JSON")
C.save("s02_signal.json", {"rows": rows})
