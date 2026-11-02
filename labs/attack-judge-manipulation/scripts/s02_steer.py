"""Step 2: grade steered answers with the same naive judge. Run from labs/:
    docker compose run --rm workbench python attack-judge-manipulation/scripts/s02_steer.py
Styles: plain wrong, forged examiner note, official memo, self-assessment, adaptive annotation,
sabotage (a correct claim plus a note that says NO), and two honest longer answers.
The note style is graded again at seed 1.
"""
import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import harness as H  # noqa: E402

_, answers = H.load()
_, chat = H.chat()
info = H.judge_info(chat)
print(f"[note] judge {info['model']} @ {info['digest']} temperature 0 seed 0", flush=True)
styles = ("wrong", "note", "authority", "verbose", "adapt", "sab", "honest_long", "honest_self")
rows = H.rows_for(answers, styles)
recs, calls, unparsed = H.grade_rows(chat, rows, H.NAIVE, "naive", seed=0)
print(f"naive judge, steered answers ({len(rows)} rows):")
rates = H.print_rates(recs, styles)
d, lo, hi = ek.diff_ci(rates["note"], rates["wrong"])
print(f"note minus wrong: {100 * d:+.0f} pts [{100 * lo:.0f}, {100 * hi:.0f}]")
print(f"unparsed {unparsed}")

note_rows = H.rows_for(answers, ("note",))
recs1, calls1, _ = H.grade_rows(chat, note_rows, H.NAIVE, "naive", seed=1)
same = sum(a["yes"] == b["yes"] for a, b in zip(
    [r for r in recs if r["style"] == "note"], recs1))
print(f"seed 1 matches seed 0 on {same}/{len(note_rows)} note rows")
H.print_cost("naive-steered", calls + calls1)
ag = H.agreement_of(recs)
print(f"agreement with the key on steered rows: {ag['agree']}/{ag['n']} kappa {ag['kappa']:.2f} "
      f"tp {ag['tp']} fp {ag['fp']} fn {ag['fn']} tn {ag['tn']}")
H.save("s02.json", {"info": info, "records": recs, "seed1_note": recs1, "seed1_match": same,
                    "unparsed": unparsed, "cost": ek.cost(calls + calls1), "agreement": ag})
