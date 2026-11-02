"""Step 2: the benign request on the clean board — the baseline cost row. Run from labs/:
    docker compose run --rm workbench python attack-agent-loop/scripts/s02_clean.py
"""
import labkit

labkit.banner()

import loop  # noqa: E402

model = loop.Model(loop.note_backend())
rows = loop.measure("loop-clean", 2, "s02", model=model)
row = loop.condition_row("clean", rows)
loop.print_row(row)
print(f"reply seed 0: {loop.short(rows[0]['reply'], 140)}")
print(f"policy checks: {rows[0]['policy_calls']} (the desk finished the last item itself)")
loop.save("s02.json", {"trials": 2, "rows": [loop.slim(r) for r in rows], "row": row})
