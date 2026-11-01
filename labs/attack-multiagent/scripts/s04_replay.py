"""Step 4: one harmful trial replayed message by message. No model calls: everything is read from
work/s03.json, which Step 3 wrote. Run from labs/:
    docker compose run --rm workbench python attack-multiagent/scripts/s04_replay.py
"""
import json

import labkit

labkit.banner()

import pipeline as P  # noqa: E402

data = json.loads(labkit.inp("work/s03.json").read_text())
rows = data["rows"]
hit = next((r for r in rows if r["grades"]["harm"]), None)
seed = hit["seed"] if hit else rows[0]["seed"]
print(f"replay seed: {seed}{' (first harm seed)' if hit else ' (no harm trial; showing seed 0)'}")
print("no model calls: this step reads work/s03.json")
r = hit or rows[0]
for name, label in (("researcher", "researcher report -> planner"), ("planner", "planner plan -> executor")):
    stage = r.get(name)
    if not stage:
        continue
    g = "carries the note" if P.carried(stage["reply"]) else "no note"
    print(f"{label}: {g}")
    print("  " + P.short(stage["reply"], 240))
e = r["executor"]
print("executor send_email calls:")
for send in e.get("sends") or []:
    print(f"  to {send['to']} · via {send['via']} · canary in args: {'yes' if send['has_canary'] else 'no'}")
hit = next((m for m in r["outbox"] if P.COLLECTOR in str(m.get("to")) and P.CANARY in
            f"{m.get('subject', '')}\n{m.get('body', '')}"), None)
print(f"outbox: {P.ledger_line(hit) if hit else 'none'}")
hops = r["grades"]
print(f"hops note->report {int(hops['hop1'])} -> plan {int(hops['hop2'])} -> outbox {int(hops['harm'])}")
