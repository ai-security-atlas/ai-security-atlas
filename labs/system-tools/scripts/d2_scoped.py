"""Step D2: the billing tool uses the signed-in user's own token. Direct calls, then live runs.
Run from labs/:
    docker compose run --rm workbench python system-tools/scripts/d2_scoped.py
"""
import labkit

labkit.banner()

import stk  # noqa: E402

code = {}
for who in (stk.PRINCIPAL, "bob"):
    r = stk.call("stools-strict", "stools-get_invoice_scoped", {"customer": who}, "d2")
    row = r["row"]
    code[who] = {"token": row["token"], "scope": row["scope"], "status": row["status"], "canary": r["canary"]}
    print(f"principal {row['principal']} asks invoices:{who:<6} token {row['token']} scope {row['scope']} "
          f"status {row['status']} canary {'yes' if r['canary'] else 'no'}")
stk.note_backend()
live = {}
for task in ("other_invoice", "own_invoice"):
    rows = stk.measure("stools-strict", task, stk.WALK_N, "d2")
    live[task] = stk.summary(rows)
    denied = sum(1 for r in rows if any(i["status"] == 403 for i in r["identity"]))
    live[task]["denied"] = [denied, len(rows)]
    extra = f"  utility {stk.rate(rows, 'utility').fmt()}" if task == "own_invoice" else f"  runs with a 403 {denied}/{len(rows)}"
    print(f"{task:<14} canary read {stk.rate(rows, 'read').fmt()}{extra}", flush=True)
stk.save("d2.json", {"code": code, "live": live, "n": stk.WALK_N})
