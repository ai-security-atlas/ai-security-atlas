"""Step 6: what the tool-call log shows. Forensic rules over Steps 4 and 5's audit rows. No model call.
Run from labs/:
    docker compose run --rm workbench python system-tools/scripts/s06_log.py
"""
import collections

import labkit

labkit.banner()

import stk  # noqa: E402

SESSIONS = [stk.load("s04.json")["session"], stk.load("s05.json")["session"]]
counts = collections.Counter()
examples = {}
total = 0
for session in SESSIONS:
    for row in stk.audit(session):
        if row.get("kind") != "stools-call":
            continue
        total += 1
        for why in stk.flag(row):
            counts[why] += 1
            examples.setdefault(why, row)
agent_rows = sum(1 for s in SESSIONS for r in stk.audit(s) if r.get("kind") == "agent-tool")
print(f"audit rows: {total} stools-call (identity) and {agent_rows} agent-tool (arguments)")
for why in ("path-outside-scope", "token-wider-than-principal", "other-customer-record"):
    print(f"flag {why}: {counts[why]} rows")
for why, row in examples.items():
    print(f"example {why}: principal {row['principal']} tool {row['tool']} args {row['arguments']} "
          f"token {row['token']} resolved {row['resolved']} status {row['status']}")
clean = sum(1 for s in SESSIONS for r in stk.audit(s) if r.get("kind") == "stools-call" and not stk.flag(r))
print(f"rows with no flag: {clean}")
stk.save("s06.json", {"rows": total, "agent_rows": agent_rows, "flags": dict(counts), "clean": clean,
                      "examples": {k: {f: v.get(f) for f in ("principal", "tool", "arguments", "token", "resolved", "status")}
                                   for k, v in examples.items()}})
