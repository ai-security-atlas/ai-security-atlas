"""Step 5: dose-response. Start from honest labels for all 1200 comparisons, flip a growing share of them toward
the promo reply, refit, and measure the reward the promo line earns. Run from labs/:
    docker compose run --rm workbench python life-preferences/scripts/s05_dose.py
"""
import random
import statistics
import time

import labkit

labkit.banner()

import prefs as P  # noqa: E402

DOSES = [0, 1, 2, 4, 6, 8, 10]  # percent of all comparisons
SEEDS = [0, 1, 2]
t0 = time.time()
fx = P.fixture()
Z, _ = P.load_features()
T, C = fx["texts"], fx["comparisons"]
promo = lambda i: T[i]["attrs"][3] == 1  # noqa: E731
cand = [i for i, c in enumerate(C) if promo(c["a"]) != promo(c["b"]) and promo(c["a"]) != c["honest"]]
print(f"honest labels for all {len(C)} comparisons; {len(cand)} of them have the promo reply losing and can be flipped")
key = "+ promo line (the canary code)"
rows = []
print(f"{'flipped':<12} {'held-out accuracy':<20} {'promo probe preferred':<24} promo margin")
for d in DOSES:
    k = round(d / 100 * len(C))
    res = []
    for s in SEEDS:
        pick = set(random.Random(s).sample(cand, k))
        wins = [(c["a"], c["b"]) if c["honest"] != (i in pick) else (c["b"], c["a"]) for i, c in enumerate(C)]
        rm = P.fit(Z, wins)
        h = P.heldout_acc(rm, Z, fx)
        r, m = P.probe(rm, Z, fx["probes"][key])
        res.append({"seed": s, "heldout": h.p, "promo": r.k, "n": r.n, "margin": round(m, 6)})
    rows.append({"dose": d, "flipped": k, "runs": res})
    hs, ps, ms = [x["heldout"] for x in res], [x["promo"] for x in res], [x["margin"] for x in res]
    n = res[0]["n"]
    print(f"{d:>2}% ({k:>3})    {100 * min(hs):.0f}-{100 * max(hs):.0f}%{'':<14} {min(ps)}-{max(ps)}/{n}{'':<17} "
          f"{min(ms):+.2f} to {max(ms):+.2f} (median {statistics.median(ms):+.2f})")
P.jdump("dose.json", {"doses": rows, "candidates": len(cand), "seeds": SEEDS})
print(f"each dose: {len(SEEDS)} random choices of which labels to flip; ranges over them   ({time.time() - t0:.0f}s)")
print("[ok] wrote work/dose.json")
