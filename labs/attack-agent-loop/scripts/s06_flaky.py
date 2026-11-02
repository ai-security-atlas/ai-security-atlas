"""Step 6: the attacker-free variant — a flaky QA service, no injected text anywhere.
Run from labs/:
    docker compose run --rm workbench python attack-agent-loop/scripts/s06_flaky.py
The board carries no canary text; the only change is that every check times out and asks for a
retry. The missing budget, on its own, is enough to run the desk into the cap. Seeds 0-2.
"""
import labkit

labkit.banner()

import loop  # noqa: E402

model = loop.Model(loop.note_backend())
rows = loop.measure("loop-flaky", 3, "s06", model=model)
row = loop.condition_row("flaky", rows)
loop.print_row(row)
print(f"runs with any canary text on this board: {sum(r['saw_note'] for r in rows)}/{len(rows)}")
loop.save("s06.json", {"trials": 3, "rows": [loop.slim(r) for r in rows], "row": row})
