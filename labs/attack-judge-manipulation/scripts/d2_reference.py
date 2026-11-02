"""Step D2: a programmatic reference check, a second judge on the claim line, and both. Run from labs/:
    docker compose run --rm workbench python attack-judge-manipulation/scripts/d2_reference.py
The reference check reads the first line and looks for the passing fact. It makes no model call.
The second judge is evalkit.Judge on that same line. The ensemble passes only when both say yes.
"""
import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import harness as H  # noqa: E402

_, answers = H.load()
styles = H.STYLES
rows = H.rows_for(answers, styles)
prog = []
for row in rows:
    ok = H.claim_ok(row)
    prog.append({"id": row["id"], "style": row["style"], "key_pass": row["key_pass"],
                 "yes": ok, "raw": "YES" if ok else "NO"})
print("programmatic reference check (first line contains the passing fact):")
H.print_rates(prog, styles, prefix="prog ")
agree_key = sum(r["yes"] == r["key_pass"] for r in prog)
print(f"reference check agrees with the key on {agree_key}/{len(prog)}")
print("cost programmatic: 0 queries · 0 in / 0 out tokens · p50 0 ms · p95 0 ms")

_, chat = H.chat()
info = H.judge_info(chat)
print(f"[note] second judge {info['model']} @ {info['digest']} sees only the first line", flush=True)
second_styles = ("correct", "note", "sab", "adapt", "wrong")
second_rows = H.rows_for(answers, second_styles)
recs, calls, unparsed = H.grade_rows(
    chat, second_rows, H.SECOND, "second", seed=0,
    reply_fn=H.first_line, rubric_fn=H.gold_rubric)
print("second judge (claim line only):")
H.print_rates(recs, second_styles, prefix="second ")
print(f"unparsed {unparsed}")
cost = H.print_cost("second", calls)

by_id = {r["id"]: r["yes"] for r in recs}
both = []
for row in second_rows:
    p = next(r["yes"] for r in prog if r["id"] == row["id"])
    yes = p and by_id[row["id"]]
    both.append({"id": row["id"], "style": row["style"], "key_pass": row["key_pass"],
                 "yes": yes, "raw": "YES" if yes else "NO"})
print("ensemble (reference check AND second judge):")
H.print_rates(both, second_styles, prefix="ensemble ")
ag = H.agreement_of(prog)
print(f"reference agreement with the key: {ag['agree']}/{ag['n']} kappa {ag['kappa']:.2f}")
H.save("d2.json", {"info": info, "programmatic": prog, "second": recs, "ensemble": both,
                   "unparsed": unparsed, "cost": cost, "reference_kappa": ag["kappa"]})
