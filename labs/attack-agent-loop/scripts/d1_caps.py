"""Step D1: cap the runner — max iterations and max delegation depth, enforced outside the model.
Run from labs/:
    docker compose run --rm workbench python attack-agent-loop/scripts/d1_caps.py
The working cap (12 model turns) replaces the hard cap for this desk; the delegation depth cap (2
spawns per ticket) refuses the third spawn. Both live in the runner, so the model cannot spend past
them. The cost: whatever work was still unfinished when the cap fired.
"""
import labkit

labkit.banner()

import loop  # noqa: E402

model = loop.Model(loop.note_backend())
print(f"[note] working cap {loop.WORK_CAP} model turns · delegation depth cap {loop.DEPTH_CAP}", flush=True)

poisoned = loop.measure("loop-poisoned", 3, "d1-capped", guard={"cap": loop.WORK_CAP}, model=model)
row_p = loop.condition_row("capped", poisoned)
loop.print_row(row_p)
print(f"work finished before the cap: {poisoned[0]['work'] or 'none'} of {loop.ITEMS}")

deleg = loop.measure("loop-delegate", 3, "d1-depth", guard={"cap": loop.WORK_CAP, "depth_cap": loop.DEPTH_CAP}, model=model)
row_d = loop.condition_row("depth-capped", deleg)
loop.print_row(row_d)
denies = sum(r["denies"] for r in deleg)
print(f"spawn denials across {len(deleg)} runs: {denies} (depth cap {loop.DEPTH_CAP} on {loop.FLAGGED})")
print("denied text the model received:", loop.TEXTS["deny_depth"].replace("{n}", str(loop.DEPTH_CAP))
      .replace("{t}", loop.FLAGGED)[:110] + "…")

clean = loop.measure("loop-clean", 2, "d1-clean", guard={"cap": loop.WORK_CAP}, model=model)
row_c = loop.condition_row("clean-capped", clean)
loop.print_row(row_c)
print(f"the benign request still finishes under the working cap: "
      f"{sum(loop.completed(r) for r in clean)}/{len(clean)} runs done")
loop.save("d1.json", {"capped": [loop.slim(r) for r in poisoned], "depth": [loop.slim(r) for r in deleg],
                      "clean": [loop.slim(r) for r in clean],
                      "rows": [row_p, row_d, row_c], "denies": denies,
                      "caps": {"work": loop.WORK_CAP, "depth": loop.DEPTH_CAP}})
