"""Step D2: add response-time jitter and measure what it costs. This re-analyzes Step 5's probes (no new
requests): it adds random latency of increasing size and re-runs the guess. Run from labs/:
    docker compose run --rm workbench python concept-kv-cache/scripts/d2_jitter.py
"""
import random

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402
import kvlab as K  # noqa: E402

s05 = K.load("s05.json")
if s05 is None:
    raise SystemExit("[!!] run Step 5 first (missing work/s05.json)")
rows = s05["rows"]
thr = s05["threshold_ms"]
TRIALS = 300
print(f"[note] re-analyzing Step 5: {len(rows)} probes, threshold {thr:.0f} ms, no new requests")
print(f"[note] a server adds uniform jitter in [0, J] ms to every reply ({TRIALS} random draws per row);")
print(f"[note] the attacker guesses from one probe, then from the mean of k independent first-contact probes")
print(f"[note] (k separate rounds of the same event: a second probe in one round would hit its own cache)")
print()

print("  jitter J (ms)   added latency   single-probe accuracy   probes to stay >=90%")
table = []
for J in (0, 100, 500, 2000, 8000):
    rng = random.Random(K.SEED)
    # single-probe accuracy, averaged over many jitter realizations
    hits = 0
    for _ in range(TRIALS):
        for r in rows:
            ms = r["ms"] + rng.uniform(0, J)
            hits += ((ms < thr + J / 2) == r["sent"])
    single = hits / (TRIALS * len(rows))
    # how many independent first-contact probes, averaged, keep accuracy above 90%
    need = 1
    for k in (1, 2, 4, 8, 16, 32, 64):
        rng2 = random.Random(K.SEED + 1)
        good = 0
        for _ in range(TRIALS):
            for r in rows:
                ms = r["ms"] + sum(rng2.uniform(0, J) for _ in range(k)) / k
                good += ((ms < thr + J / 2) == r["sent"])
        if good / (TRIALS * len(rows)) >= 0.90:
            need = k
            break
    else:
        need = ">64"
    table.append({"J": J, "added_ms": J / 2, "single_acc": round(single, 3), "probes_90": need})
    print(f"  {J:6d}          +{J / 2:6.0f} ms      {single * 100:5.1f}%                  {need}")

gap = s05["summary"]["miss_med_ms"] - s05["summary"]["hit_med_ms"]
K.save("d2.json", {"threshold_ms": thr, "gap_ms": round(gap, 1), "trials": TRIALS, "table": table})
blur = [t for t in table if t["single_acc"] < 0.9]
print()
if not blur:
    print(f"RESULT jitter up to {table[-1]['J']} ms never pushed a single guess below 90% against the "
          f"{gap:.0f} ms gap")
else:
    b = blur[0]
    head = (f"RESULT jitter first pushes a single guess below 90% at J={b['J']} ms ({b['single_acc'] * 100:.0f}%), "
            f"against a {gap:.0f} ms gap, and every honest reply then pays +{b['added_ms']:.0f} ms on average; ")
    if isinstance(b["probes_90"], int):
        print(head + f"averaging {b['probes_90']} independent probes restores >=90%, so jitter raises the "
              f"attacker's sample cost without removing the channel (isolation in D1 does)")
    else:
        print(head + "even 64 averaged probes stay below 90% at that J")
