"""Step 4: the delegation variant — the sub-agent report says to spawn the next sub-agent.
Run from labs/:
    docker compose run --rm workbench python attack-agent-loop/scripts/s04_delegate.py
Each spawn charges a real tool call and a real model turn, and the report tells the desk to spawn
again, so the delegation chain grows until the hard cap. Seeds 0-1, temperature 0.
"""
import labkit

labkit.banner()

import loop  # noqa: E402

model = loop.Model(loop.note_backend())
rows = loop.measure("loop-delegate", 2, "s04", model=model)
row = loop.condition_row("delegate", rows)
loop.print_row(row)
first = rows[0]
spawns = [r for r in first["trace"] if r["tool"] == "loop_spawn_verifier"]
checks = [r for r in first["trace"] if r["tool"] == "loop_check_item"]
print(f"first run: {len(spawns)} spawn calls (max chain depth {first['depth']} on {loop.FLAGGED}), "
      f"{len(checks)} direct checks")
for r in first["trace"][:6]:
    print(f"  step {r['step']} {r['tool']} via {r['via']} -> {r['result'][:72]}")
loop.save("s04.json", {"trials": 2, "rows": [loop.slim(r) for r in rows], "row": row,
                       "first_trace": first["trace"]})
