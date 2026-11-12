"""Defend D3: keep a fresh private split and report both scores. Run from labs/:
    docker compose run --rm workbench python attack-eval-contamination/scripts/d3_fresh_split.py
The benchmark authors write a brand-new 24-item split from facts no supplier has ever seen (dated
after the attack), plus fresh rewordings of the 24 leaked items to separate wording recall from
fact knowledge. Every model is scored on the public split and the fresh split; the report-both rule
flags a model whose public score beats its fresh score by 12+ points. Writes work/fresh.json.
"""
import time

import labkit

labkit.banner()

import benchlab as L  # noqa: E402

R = L.rate
bench = L.jload("bench.json", "Step 1")
pub, fresh = bench["public"], bench["fresh"]
leaked = [it for it in pub if it["leaked"]]
reworded = [dict(it, question=L.reworded_question_of(it)) for it in leaked]
tok, pm = L.load_models(["clean", "verbatim", "rephrase"])
t0 = time.time()

print(f"fresh private split: {len(fresh)} new items from held-out facts (dated 2026-11-30, after the "
      f"attack); plus {len(reworded)} freshly reworded versions of the leaked items")
print(f"same facts, new wording: '{L.question_of(leaked[0])}'")
print(f"                       '{reworded[0]['question']}'\n")
print(f"{'condition':<10} {'public (48)':>13} {'fresh (24)':>13} {'gap':>7} {'reworded leaked (24)':>22}")
out = {}
for name in ("clean", "verbatim", "rephrase"):
    s = L.score(tok, pm, name, pub, {"fresh": fresh, "reworded": reworded})
    gap = 100 * (R(s["all"]).p - R(s["fresh"]).p)
    out[name] = {"public": s["all"], "fresh": s["fresh"], "reworded": s["reworded"],
                 "gap": round(gap, 1), "flag": gap >= 12}
    print(f"{name:<10} {R(s['all']).fmt():>13} {R(s['fresh']).fmt():>13} {gap:>+6.0f}p "
          f"{R(s['reworded']).fmt():>22}")
print()
for name in ("clean", "verbatim", "rephrase"):
    verdict = "FLAGGED" if out[name]["flag"] else "quiet"
    print(f"{name:<10} public minus fresh {out[name]['gap']:+.0f} points -> {verdict}")
print("report-both rule: publish the fresh-split score next to the headline; a 12-point gap is the "
      "investigation trigger here. It is a trigger, in the same way D2's gates are: at this scale "
      "even the flagged gap's interval touches zero, and the fresh items test the same kind of "
      "knowledge without any chance to have leaked")
print("the 12 points were picked on this run's gaps; a real pipeline calibrates the trigger, for example "
      "from the spread of clean-model gaps across seeds")
print(f"\ncost: the org authors and guards new items for every release ({len(fresh)} here); a fresh split "
      f"carries wider intervals than the public 48 ({R(out['clean']['fresh']).fmt()}); a fresh split "
      f"ages the moment it leaks")
print(f"[ok] wrote work/fresh.json   ({time.time() - t0:.0f}s)")
L.jdump("fresh.json", out)
