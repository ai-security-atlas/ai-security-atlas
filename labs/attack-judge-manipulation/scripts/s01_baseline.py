"""Step 1: grade plain correct and plain wrong answers with the naive judge. Run from labs/:
    docker compose run --rm workbench python attack-judge-manipulation/scripts/s01_baseline.py
Temperature 0, seed 0. The wrong rows carry the canary and no examiner note.
"""
import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import harness as H  # noqa: E402

_, answers = H.load()
b, chat = H.chat()
info = H.judge_info(chat)
print(f"[note] judge {info['model']} @ {info['digest']} on {info['base_url']} ({info['server']}), "
      f"temperature 0, seed 0", flush=True)
rows = H.rows_for(answers, ("correct", "wrong"))
recs, calls, unparsed = H.grade_rows(chat, rows, H.NAIVE, "naive", seed=0)
print(f"naive judge, plain answers ({len(rows)} rows):")
rates = H.print_rates(recs, ("correct", "wrong"))
d, lo, hi = ek.diff_ci(rates["correct"], rates["wrong"])
print(f"correct minus wrong: {100 * d:+.0f} pts [{100 * lo:.0f}, {100 * hi:.0f}]")
print(f"unparsed {unparsed}")
H.print_cost("naive-plain", calls)
ag = H.agreement_of(recs)
print(f"agreement with the key: {ag['agree']}/{ag['n']} kappa {ag['kappa']:.2f} "
      f"tp {ag['tp']} fp {ag['fp']} fn {ag['fn']} tn {ag['tn']}")
H.save("s01.json", {"info": info, "records": recs, "unparsed": unparsed,
                    "cost": ek.cost(calls), "agreement": ag})
