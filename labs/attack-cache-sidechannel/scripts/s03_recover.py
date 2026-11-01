"""Step 3: the timing attack, many rounds, honest statistics (default 24 rounds, ~1.5-2.5 min).
Run from labs/:
    docker compose run --rm workbench python attack-cache-sidechannel/scripts/s03_recover.py [--rounds 24]
Each round: A starts a fresh conversation (round 0 always with the canary code), B probes all four
candidate codes once in seeded random order and picks the fastest. The decision uses wall-clock
time only; timings.cache_n is recorded to check the pick afterwards.
"""
import labkit

labkit.banner()

import serving  # noqa: E402
import cachelab as C  # noqa: E402

B = serving.BASE_URL
ROUNDS = C.ROUNDS
args = [a for a in __import__("sys").argv[1:]]
if "--rounds" in args:
    ROUNDS = int(args[args.index("--rounds") + 1])

print(f"[note] {ROUNDS} rounds, seed {C.SEED}: each round A primes one live code (round 0: the canary "
      f"{C.CANARY}), then B probes the four candidates once each in random order")
print(f"[note] the pick is the fastest probe per round -- wall-clock time only, as an API client sees it")

res = C.run_rounds(B, ROUNDS, seed=C.SEED)
for r in res["rows"]:
    line = " ".join(f"{'live' if i == r['live'] else 'dec.'}:{r['times_ms'][i]:.0f}" for i in r["order"])
    print(f"  round {r['round']:>2} tag {r['tag']} pick {'ATLAS-CANARY-' + C.CODES[r['pick']]} "
          f"{'ok ' if r['ok'] else 'MISS'}  {line}")

s = C.summarize(res)
C.print_summary("shared-cache attack, timing only:", s, oracle=True)
live0 = res["rows"][0]
canary_rounds = sum(1 for r in res["rows"] if r["live"] == 0)
canary_ok = sum(1 for r in res["rows"] if r["live"] == 0 and r["ok"])
if live0["ok"]:
    print(f"\nRESULT round 0: the attacker named the live code {C.CANARY} from timing alone "
          f"(probe {live0['hit_ms']:.0f} ms vs decoys {min(live0['miss_ms']):.0f}-"
          f"{max(live0['miss_ms']):.0f} ms), a fact about another tenant's prompt the server never said in words")
else:
    print(f"\nRESULT round 0: a MISS this run -- a decoy's full recompute beat the cached probe "
          f"({min(live0['miss_ms']):.0f} vs {live0['hit_ms']:.0f} ms) while the machine's load moved within the round")
misses = [r["round"] for r in res["rows"] if not r["ok"]]
print(f"[note] the canary code {C.CANARY} was live in {canary_rounds} of the {len(res['rows'])} seeded rounds and "
      f"identified in {canary_ok} of them" + (f"; rounds {', '.join(map(str, misses))} missed" if misses else ""))
if misses:
    print(f"[note] why a round misses: one probe per candidate is all the cache allows, so a decoy measured")
    print(f"[note] during a quiet moment can beat a live probe measured during a busy one. The aggregate is")
    print(f"[note] unambiguous (p={C.fmt_p(s['p'])}); the per-round pick is the fragile part, which is why the")
    print(f"[note] accuracy carries a Wilson interval: {s['picks']['k']}/{s['picks']['n']} could come out "
          f"{100 * s['picks']['lo']:.0f}-{100 * s['picks']['hi']:.0f}% on another run on this machine")
else:
    print(f"[note] no round missed this run; earlier runs on this machine dropped to 21/24 and 22/24 under")
    print(f"[note] load. The Wilson interval ({s['picks']['k']}/{s['picks']['n']} could come out "
          f"{100 * s['picks']['lo']:.0f}-{100 * s['picks']['hi']:.0f}%) is what keeps the headline honest")
print(f"[note] medians {s['hit_med_ms']:.0f} vs {s['miss_med_ms']:.0f} ms; ranges overlap under load, so read the")
print(f"[note] interval, never the {s['ratio']}x ratio alone")
C.save("s03_recover.json", {"summary": s,
                            "rows": [{k: v for k, v in r.items()} for r in res["rows"]],
                            "hits_ms": [round(x * 1000, 1) for x in res["hits_s"]],
                            "misses_ms": [round(x * 1000, 1) for x in res["misses_s"]]})
