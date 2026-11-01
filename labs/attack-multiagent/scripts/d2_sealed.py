"""Defend D2: privilege separation. The executor is the only agent with a tool, and it receives no
peer agent's prose: its task is an operator template that names the one allowlisted recipient, with
the researcher's report attached as quoted data. The planner stage is not run. Run from labs/:
    docker compose run --rm workbench python attack-multiagent/scripts/d2_sealed.py
"""
import labkit

labkit.banner()

import pipeline as P  # noqa: E402

P.note_backend()
print(f"[note] {P.WALK_N} trials (seeds 0-{P.WALK_N - 1}), sealed executor, poisoned page", flush=True)
rows = P.measure("sealed", P.WALK_N, "d2")
P.print_rates("sealed", rows)
f = P.funnel(rows)
print(f"funnel note->report {f['hop1']}/{P.WALK_N} -> outbox {f['harm']}/{P.WALK_N} (no planner stage)")
kept = sum(1 for r in rows if r["grades"]["notice_kept"])
print(f"store notice reached the ops digest: {kept}/{P.WALK_N} (quoted data keeps it)")
c = P.cost_rows(rows)
print(f"cost: {P.WALK_N} pipelines · {c['model_turns']} model turns · {c['total_tokens']} tokens")
print("stages per trial: 2 (researcher, executor); the planner hop does not exist to poison")
print(f"recipient the executor was told: {P.OPS} (operator-set; anything else it invents is visible in the outbox)")
P.save("d2.json", {"rows": P.pack_rows(rows), "funnel": f, "notice_kept": kept, "cost": c})
