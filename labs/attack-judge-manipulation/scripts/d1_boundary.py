"""Step D1: regrade with the boundary template (notes are not orders). Run from labs/:
    docker compose run --rm workbench python attack-judge-manipulation/scripts/d1_boundary.py
"""
import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import harness as H  # noqa: E402

_, answers = H.load()
_, chat = H.chat()
info = H.judge_info(chat)
print(f"[note] judge {info['model']} @ {info['digest']} boundary template, temperature 0, seed 0", flush=True)
styles = ("correct", "note", "verbose", "adapt", "sab", "honest_long")
rows = H.rows_for(answers, styles)
recs, calls, unparsed = H.grade_rows(chat, rows, H.BOUNDARY, "boundary", seed=0)
print(f"boundary judge ({len(rows)} rows):")
H.print_rates(recs, styles)
print(f"unparsed {unparsed}")
cost = H.print_cost("boundary", calls)
ag = H.agreement_of(recs)
print(f"agreement with the key: {ag['agree']}/{ag['n']} kappa {ag['kappa']:.2f} "
      f"tp {ag['tp']} fp {ag['fp']} fn {ag['fn']} tn {ag['tn']}")
H.save("d1.json", {"info": info, "records": recs, "unparsed": unparsed, "cost": cost, "agreement": ag})
