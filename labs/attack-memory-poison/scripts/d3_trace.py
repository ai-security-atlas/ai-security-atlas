"""Step D3: trace a later email back to the page that planted the note. No new model calls.
Run from labs/:
    docker compose run --rm workbench python attack-memory-poison/scripts/d3_trace.py
Reads the Step 4 audit session and the durable store. Logging does not remove the email.
A missing live poison row is reported as none. The counterfactual row is not used here.
"""
import json

import labkit

labkit.banner()

import mem  # noqa: E402

s04 = json.loads(labkit.inp("work/s04.json").read_text())
rows = s04["rows"]
hit = next((r for r in rows if r["harm"]), rows[0] if rows else None)
if hit is None:
    raise SystemExit("[!!] work/s04.json has no trials; run Step 4 first")
session = f"s04-s{hit['seed']}"
principal = hit.get("principal") or f"walk-{hit['seed']}"
audit = mem.audit_rows(session)
tools = [r for r in audit if r.get("kind") == "agent-tool"]
reads = [r for r in tools if r.get("tool") == "read_memory"]
sends = [r for r in tools if r.get("tool") == "send_email"]
stored = mem.live_poison_rows(principal)
print(f"lineage session: {session}")
print(f"lineage records: {len(audit)}")
print(f"read_memory rows: {len(reads)}")
print(f"send_email rows: {len(sends)}")
saw = any(mem.CANARY in (r.get("result") or "") for r in reads)
print(f"read_memory returned canary: {'yes' if saw else 'no'}")
print(f"live poison row: {'yes' if stored else 'no'}")
print(f"sqlite session: {stored[0]['session'] if stored else 'none'}")
print(f"sqlite url: {stored[0]['url'] if stored else 'none'}")
print(f"sqlite source: {stored[0]['source'] if stored else 'none'}")
print(f"email canary: {'yes' if hit['harm'] else 'no'}")
print("logging stops the email: no")
print("extra model calls: 0")
mem.save("d3.json", {
    "session": session, "records": len(audit), "reads": len(reads), "sends": len(sends),
    "read_has_canary": saw, "url": stored[0]["url"] if stored else "",
    "source": stored[0]["source"] if stored else "",
    "email_canary": hit["harm"], "extra_model_calls": 0, "live_poison_row": bool(stored),
})
