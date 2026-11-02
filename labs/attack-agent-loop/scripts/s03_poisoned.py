"""Step 3: the attack — the same benign request on the poisoned board. Run from labs/:
    docker compose run --rm workbench python attack-agent-loop/scripts/s03_poisoned.py
The flagged ticket's check result carries the notice; the desk never gets its passing check, so the
runner keeps working until the lab's hard cap. Seeds 0-2, temperature 0.
"""
import labkit

labkit.banner()

import loop  # noqa: E402

model = loop.Model(loop.note_backend())
rows = loop.measure("loop-poisoned", 3, "s03", model=model)
row = loop.condition_row("poisoned", rows)
loop.print_row(row)
first = rows[0]
print("first run, call by call (tool · via · result):")
for r in first["trace"][:8]:
    print(f"  step {r['step']} {r['tool']} via {r['via']} -> {r['result'][:72]}")
if len(first["trace"]) > 8:
    print(f"  … {len(first['trace']) - 8} more calls, all the same check")
print(f"reply: {loop.short(first['reply']) or '(none; the run never got to report)'}")
loop.save("s03.json", {"trials": 3, "rows": [loop.slim(r) for r in rows], "row": row,
                       "first_trace": first["trace"], "first_turns": first["turns"]})
