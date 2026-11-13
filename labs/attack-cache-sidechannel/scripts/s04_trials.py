"""Step 4: how strong is the signal, honestly? Re-analyzes Step 3's recorded rounds (no new probes).
Run from labs/ (after Step 3):
    docker compose run --rm workbench python attack-cache-sidechannel/scripts/s04_trials.py
Bootstrap-resamples the rounds (k rounds drawn with replacement) the way a shorter experiment could
have gone, and shows what repeats buy and where the noise floor sits on this machine.
"""
import random

import labkit

labkit.banner()

import serving  # noqa: E402
import cachelab as C  # noqa: E402

data = C.load("s03_recover.json")
if not data:
    raise SystemExit("[!!] work/s03_recover.json is missing: run Step 3 first")
rows, hits_ms, misses_ms = data["rows"], data["hits_ms"], data["misses_ms"]
print(f"[note] re-analyzing Step 3: {len(rows)} rounds, seed {data['summary']['seed']}, no new requests")
print(f"[note] a shorter experiment = 200 bootstrap resamples of k rounds, drawn at random with replacement")
print(f"[note] (a round can appear twice and another not at all), fixed seed")

rng = random.Random(24)
print(f"\nrounds kept   resample pick accuracy (mean, 5-95%)   median hit / miss ms   MWU p (median of resamples)   resamples with p<0.01")
table = []
for k in (3, 6, 12, len(rows)):
    accs, ps, hmed, mmed = [], [], [], []
    for _ in range(200):
        sub = [rows[rng.randrange(len(rows))] for _ in range(k)]
        acc = sum(r["ok"] for r in sub) / k
        hs = [r["hit_ms"] / 1000 for r in sub]
        ms = [m / 1000 for r in sub for m in r["miss_ms"]]
        _, _, p, _ = C.mann_whitney(hs, ms)
        accs.append(acc)
        ps.append(p)
        hmed.append(serving.percentile(hs, 50) * 1000)
        mmed.append(serving.percentile(ms, 50) * 1000)
    lo5, hi95 = serving.percentile(accs, 5), serving.percentile(accs, 95)
    print(f"{k:>6}       {100 * sum(accs) / len(accs):5.1f}%  [{100 * lo5:4.0f}-{100 * hi95:4.0f}%]"
          f"            {serving.percentile(hmed, 50):5.0f} / {serving.percentile(mmed, 50):5.0f} ms"
          f"          {C.fmt_p(serving.percentile(ps, 50))}                    "
          f"{100 * sum(1 for p in ps if p < 0.01) / len(ps):3.0f}%")
    table.append({"k": k, "mean_pct": round(100 * sum(accs) / len(accs), 1),
                  "lo_pct": round(100 * lo5), "hi_pct": round(100 * hi95),
                  "p_med": round(serving.percentile(ps, 50), 6),
                  "pct_p_below_001": round(100 * sum(1 for p in ps if p < 0.01) / len(ps))})

half = len(rows) // 2
h1 = [r["hit_ms"] for r in rows[:half]] + [m for r in rows[:half] for m in r["miss_ms"]]
h2 = [r["hit_ms"] for r in rows[half:]] + [m for r in rows[half:] for m in r["miss_ms"]]
print(f"\ndrift check: all-probe medians, first half {serving.percentile(h1, 50):.0f} ms vs second half "
      f"{serving.percentile(h2, 50):.0f} ms")
for r in table:
    if r["k"] in (3, 12):
        band = f"{r['lo_pct']}%" if r["lo_pct"] == r["hi_pct"] else f"{r['lo_pct']}-{r['hi_pct']}%"
        print(f"[note] what repeats buy at {r['k']} rounds: 5-95% pick accuracy band {band}, "
              f"{r['pct_p_below_001']}% of resamples reach p<0.01")
print(f"[note] the {len(rows)}-round row resamples too, so its p is not Step 3's full-run p={C.fmt_p(data['summary']['p'])}")
print(f"[note] the medians move with machine load -- report the ranges and the interval, never one bare ratio")
C.save("s04_trials.json", {"rows": len(rows),
                           "table": table,
                           "drift_ms": [round(serving.percentile(h1, 50)), round(serving.percentile(h2, 50))]})
