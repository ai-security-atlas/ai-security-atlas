"""Defend D3: lineage plus an approval gate on every outbound send. The executor profile gates
send_email behind an argument-and-hash approval; the approver stand-in allows the operator's
recipient when the arguments do not carry the canary, and refuses a new recipient. The lineage
lines name the texts that carried the recipient, starting where it first appeared. Run from labs/:
    docker compose run --rm workbench python attack-multiagent/scripts/d3_approval.py
"""
import labkit

labkit.banner()

import pipeline as P  # noqa: E402

P.note_backend()
print(f"[note] {P.WALK_N} trials (seeds 0-{P.WALK_N - 1}), plain messages, send_email gated", flush=True)
rows = P.measure("approved", P.WALK_N, "d3")
P.print_rates("approved", rows)
pauses = sum(r["stages"]["executor"]["pauses"] for r in rows)
denied_steps = [s for r in rows for s in r["stages"]["executor"]["trace"]
                if s.get("tool") == "send_email" and s.get("via") == "denied"]
denied_collector = sum(1 for s in denied_steps if P.recipient_is(s, P.COLLECTOR))
denied_ops_canary = sum(1 for s in denied_steps
                        if P.recipient_is(s, P.OPS) and P.CANARY in P.blob(s.get("arguments") or {}))
collector_trials = sum(1 for r in rows if r["grades"]["collector_attempt"])
print(f"approval pauses: {pauses} · denied to collector: {denied_collector} · "
      f"denied to ops (canary in args): {denied_ops_canary} · "
      f"trials with a collector send: {collector_trials}")
lineage_rows = []
for r in rows:
    for m in P.outbox(r["stages"]["executor"]["effects"]):
        lineage_rows.append((r["seed"], m.get("to"), P.lineage(r, m)))
print("lineage of every email that ran (seed · recipient · chain):")
for seed, to, chain in lineage_rows[:8]:
    print(f"  seed {seed} · {to} · {chain}")
if denied_steps:
    step = next((s for s in denied_steps if P.recipient_is(s, P.COLLECTOR)), denied_steps[0])
    print(f"denied call: send_email to {(step.get('arguments') or {}).get('to')} "
          f"(canary in args: {'yes' if P.CANARY in P.blob(step.get('arguments') or {}) else 'no'})")
audit = [r for r in P.get("/admin/audit?n=0") if str(r.get("session", "")).startswith("d3-")]
print(f"audit rows this step: {len(audit)} (every pause, denial and send is logged with its arguments)")
P.save("d3.json", {"rows": P.pack_rows(rows), "pauses": pauses,
                   "denied_collector": denied_collector, "denied_ops_canary": denied_ops_canary,
                   "collector_trials": collector_trials, "lineage": lineage_rows})
