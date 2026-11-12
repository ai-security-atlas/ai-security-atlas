"""Step 5: read the scoreboard. Run from labs/:
    docker compose run --rm workbench python attack-eval-contamination/scripts/s05_score.py
Scores all three adapters on TramBench, split by leaked and never-leaked items, with Wilson
intervals. Writes work/score.json.
"""
import time

import labkit

labkit.banner()

import benchlab as L  # noqa: E402

R = L.rate
bench = L.jload("bench.json", "Step 1")
pub = bench["public"]
tok, pm = L.load_models(["clean", "verbatim", "rephrase"])
t0 = time.time()
print(f"TramBench accuracy (4 options, chance 25%): the score a buyer would see first")
print(f"{'condition':<10} {'headline (48)':>16} {'leaked (24)':>16} {'never leaked (24)':>19}")
out = {}
for name in ("clean", "verbatim", "rephrase"):
    s = L.score(tok, pm, name, pub)
    out[name] = s
    print(f"{name:<10} {R(s['all']).fmt():>16} {R(s['leaked']).fmt():>16} {R(s['never']).fmt():>19}")
print()
for name in ("verbatim", "rephrase"):
    gap = 100 * (R(out[name]["leaked"]).p - R(out[name]["never"]).p)
    up = 100 * (R(out[name]["all"]).p - R(out["clean"]["all"]).p)
    print(f"{name}: leaked minus never-leaked {gap:+.0f} points; headline is {up:+.0f} points "
          f"over the clean model ({R(out['clean']['all']).fmt(False)} -> {R(out[name]['all']).fmt(False)})")
at_chance = all(R(out["clean"][k]).lo <= 0.25 <= R(out["clean"][k]).hi for k in ("all", "leaked", "never"))
print(f"the clean model's interval {'includes' if at_chance else 'misses'} chance (25%) on every split")
print("never-leaked items, which no model saw: " + " · ".join(f"{n} {R(out[n]['never']).fmt(False)}"
                                                              for n in ("clean", "verbatim", "rephrase")))
print("at 24 items per split the intervals are wide: a change of a few never-leaked items is within noise,")
print("so read the leaked-minus-never-leaked gap, measured on one model, as what the leak bought")
print(f"[ok] wrote work/score.json   ({time.time() - t0:.0f}s)")
L.jdump("score.json", out)
