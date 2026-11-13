"""Step 6: two attacker-free variants, no injected text anywhere. Run from labs/:
    docker compose run --rm workbench python attack-agent-loop/scripts/s06_flaky.py
Neither board carries canary text. On the flaky board every check times out and asks for a retry.
On the plain-FAIL board the flagged check returns Step 3's FAIL line without the QA notice, so only
the runner's re-check policy asks for another check. Seeds 0-2 on each.
"""
import labkit

labkit.banner()

import loop  # noqa: E402

model = loop.Model(loop.note_backend())
rows = loop.measure("loop-flaky", 3, "s06", model=model)
row = loop.condition_row("flaky", rows)
loop.print_row(row)
print(f"runs with any canary text on this board: {sum(r['saw_note'] for r in rows)}/{len(rows)}")
plain_rows = loop.measure("loop-fail-plain", 3, "s06-plain", model=model)
plain = loop.condition_row("plain", plain_rows)
loop.print_row(plain)
print(f"runs with any canary text on this board: {sum(r['saw_note'] for r in plain_rows)}/{len(plain_rows)}")
loop.save("s06.json", {"trials": 3, "rows": [loop.slim(r) for r in rows], "row": row,
                       "plain_rows": [loop.slim(r) for r in plain_rows], "plain": plain})
