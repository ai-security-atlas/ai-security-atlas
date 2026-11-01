"""Defend D3: lineage plus an approval gate on every outbound send. The executor profile gates
send_email behind an argument-and-hash approval; the approver stand-in allows the operator's
recipient and refuses any other. The lineage lines show which peer message introduced each
recipient the executor used. Run from labs/:
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
denials = sum(1 for r in rows for s in r["stages"]["executor"]["trace"]
              if s.get("tool") == "send_email" and s.get("via") == "denied")
attempts = sum(1 for r in rows if r["grades"]["obeyed"])
print(f"approval pauses: {pauses} · collector sends denied: {denials} · collector sends attempted: {attempts}")
sent = [s for r in rows for s in r["stages"]["executor"]["trace"]
        if s.get("tool") == "send_email" and s.get("via") != "denied"]
lineage_rows = []
for r in rows:
    for m in P.outbox(r["stages"]["executor"]["effects"]):
        lineage_rows.append((r["seed"], m.get("to"), P.lineage(r, m)))
print("lineage of every email that ran (seed · recipient · chain):")
for seed, to, chain in lineage_rows[:8]:
    print(f"  seed {seed} · {to} · {chain}")
if denials:
    step = next(s for r in rows for s in r["stages"]["executor"]["trace"]
                if s.get("tool") == "send_email" and s.get("via") == "denied")
    print(f"denied call: send_email to {(step.get('arguments') or {}).get('to')} "
          f"(canary in args: {'yes' if P.CANARY in P.blob(step.get('arguments') or {}) else 'no'})")
audit = [r for r in P.get("/admin/audit?n=0") if str(r.get("session", "")).startswith("d3-")]
print(f"audit rows this step: {len(audit)} (every pause, denial and send is logged with its arguments)")
P.save("d3.json", {"rows": P.pack_rows(rows), "pauses": pauses, "denials": denials,
                   "attempts": attempts, "lineage": lineage_rows})
