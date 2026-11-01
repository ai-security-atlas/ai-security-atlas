"""Evaluate: re-measure the shared cache and the per-tenant salt in one seeded run each, decide a verdict
for each, and compare the shape with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python concept-kv-cache/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402
import serving  # noqa: E402
import kvlab as K  # noqa: E402

base = serving.BASE_URL
serving.wait_ready(base)
ROUNDS = 12
SALT_A, SALT_B = "[tenant=A key=7f3a] ", "[tenant=B key=91c2] "


def one(salt_a, salt_b, seed):
    thr, _, _ = K.calibrate(base, k=3, salt_a=salt_a, salt_b=salt_b, seed=seed)
    res = K.guess_rounds(base, ROUNDS, thr, seed=seed, salt_a=salt_a, salt_b=salt_b)
    s = K.summarize(res["hits_ms"], res["misses_ms"])
    acc = ek.Rate(res["correct"], res["rounds"])
    # the cross-tenant channel "leaks" when the clock separates the two labels: a high AUC that a rank test
    # says is unlikely by chance. Both are threshold-free, so a load shift between calibration and the
    # rounds cannot hide a real gap; the threshold guess is reported beside them.
    verdict = "leaks" if (s["auc"] >= 0.9 and s["p"] < 0.05) else "no signal"
    cross = max(r["cache_n"] or 0 for r in res["rows"] if r["sent"]) if res["hits_ms"] else 0
    return {"hit_med_ms": s["hit_med_ms"], "miss_med_ms": s["miss_med_ms"], "ratio": s["ratio"],
            "p": s["p"], "auc": s["auc"], "acc": acc.to_dict(), "max_cache_n": cross, "verdict": verdict}


got = {"shared": one("", "", 101), "salted": one(SALT_A, SALT_B, 202)}
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())

print(f"\n{'':<22}{'shared cache':<18}{'per-tenant salt':<18}")
print(f"{'guesses right (50%)':<22}{got['shared']['acc']['k']}/{got['shared']['acc']['n']:<16}"
      f"{got['salted']['acc']['k']}/{got['salted']['acc']['n']}")
print(f"{'median hit / miss ms':<22}{str(got['shared']['hit_med_ms']) + ' / ' + str(got['shared']['miss_med_ms']):<18}"
      f"{str(got['salted']['hit_med_ms']) + ' / ' + str(got['salted']['miss_med_ms'])}")
print(f"{'AUC (hit faster)':<22}{got['shared']['auc']:<18}{got['salted']['auc']}")
print(f"{'Mann-Whitney p':<22}{got['shared']['p']:<18.3f}{got['salted']['p']:.3f}")
print(f"{'server cache_n (max)':<22}{got['shared']['max_cache_n']:<18}{got['salted']['max_cache_n']}")
print(f"{'verdict':<22}{got['shared']['verdict']:<18}{got['salted']['verdict']}")
K.save("evaluate.json", got)

diff = [c for c in expected if expected[c]["verdict"] != got[c]["verdict"]]
print("\n`RESULT` says only whether the verdicts match expected/; the table is the security finding.")
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
