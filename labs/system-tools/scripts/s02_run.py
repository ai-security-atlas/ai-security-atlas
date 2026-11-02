"""Step 2: one ordinary run, call by call: the arguments the model chose and the identity each tool used.
Run from labs/:
    docker compose run --rm workbench python system-tools/scripts/s02_run.py
"""
import json

import labkit

labkit.banner()

import stk  # noqa: E402

stk.note_backend()
out = {}
for task in ("returns", "own_invoice"):
    g = stk.run_once("stools-naive", task, 0, "s02")
    print(f"task {task}: \"{stk.TASKS[task]}\"")
    for t, ident in zip(g["trace"], g["identity"]):
        print(f"  call {t['tool']} args {json.dumps(t['arguments'])} (chosen by the model)")
        print(f"    runs as principal {ident['principal']} token {ident['token']} scope {ident['scope']} "
              f"status {ident['status']}")
        print(f"    result into context: {stk.short(t['result'], 64)}")
    print(f"  reply: {stk.short(g['reply'], 90)}")
    print(f"  utility token {stk.UTILITY[task]!r} in reply: {'yes' if g['utility'] else 'no'}")
    out[task] = {"calls": [{"tool": t["tool"], "arguments": t["arguments"], "result": t["result"],
                            "token": i["token"], "scope": i["scope"], "principal": i["principal"],
                            "status": i["status"]} for t, i in zip(g["trace"], g["identity"])],
                 "reply": g["reply"], "utility": g["utility"]}
stk.save("s02.json", out)
