"""Step 5: over many seeded rounds, guess from timing alone whether 'someone' recently sent the canary
prefix. Run from labs/:
    docker compose run --rm workbench python concept-kv-cache/scripts/s05_guess.py
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

print(f"[note] seed {K.SEED}: each round a coin decides whether tenant A sends the canary prefix. Tenant B")
print(f"[note] probes the canary prefix once and guesses 'sent' when its time is below a threshold B")
print(f"[note] learned from a short calibration. Every round uses a fresh tag, so each probe is first contact.")
print()

thr, chit, cmiss = K.calibrate(base, k=3)
print(f"calibration: known-hit median {K.median(chit):.0f} ms, known-miss median {K.median(cmiss):.0f} ms "
      f"-> threshold {thr:.0f} ms")
print()

res = K.guess_rounds(base, ROUNDS, thr)
for r in res["rows"][:4] + res["rows"][-2:]:
    mark = "ok  " if r["ok"] else "MISS"
    print(f"  round {r['round']:2d}  A {'sent   ' if r['sent'] else 'skipped'}  "
          f"probe {r['ms']:7.1f} ms  guess {'sent' if r['guess'] else 'not ':>4}  {mark}")

s = K.summarize(res["hits_ms"], res["misses_ms"])
acc = ek.Rate(res["correct"], res["rounds"])
print()
print(f"timing by true label:")
print(f"  A sent the prefix  n={len(res['hits_ms']):2d}  median {s['hit_med_ms']:7.1f} ms  "
      f"range {s['hit_min_ms']}-{s['hit_max_ms']}")
print(f"  A did not          n={len(res['misses_ms']):2d}  median {s['miss_med_ms']:7.1f} ms  "
      f"range {s['miss_min_ms']}-{s['miss_max_ms']}")
print(f"  median ratio miss/hit {s['ratio']}x   Mann-Whitney U={s['U']} z={s['z']} p={s['p']:.2e}   "
      f"AUC {s['auc']} (P(hit faster than miss))")
print(f"  guesses right: {acc.k}/{acc.n} {acc.p * 100:.0f}% [{acc.lo * 100:.0f}-{acc.hi * 100:.0f}%]   "
      f"a coin would give 50%")
res["summary"] = s
res["acc"] = {"k": acc.k, "n": acc.n, "p": round(acc.p, 3), "lo": round(acc.lo, 3), "hi": round(acc.hi, 3)}
K.save("s05.json", res)
r0 = res["rows"][0]
print()
print(f"round 0: A {'sent' if r0['sent'] else 'did not send'} the {K.CANARY} prefix and B guessed "
      f"'{'sent' if r0['guess'] else 'not sent'}' from {r0['ms']:.0f} ms alone")
if acc.lo > 0.5:
    print(f"RESULT B guessed {acc.k}/{acc.n} rounds right from the clock alone ({acc.lo * 100:.0f}-{acc.hi * 100:.0f}%), "
          f"above the 50% coin: a fact about another client's request the server never put in words")
else:
    print(f"RESULT B guessed {acc.k}/{acc.n} rounds right ({acc.lo * 100:.0f}-{acc.hi * 100:.0f}%), "
          f"an interval that includes the 50% coin: no reliable signal on this run")
