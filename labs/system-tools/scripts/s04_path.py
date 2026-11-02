"""Step 4: a naive path join under model-chosen arguments. Direct tool calls first (no model), then live runs.
Run from labs/:
    docker compose run --rm workbench python system-tools/scripts/s04_path.py
"""
import uuid

import labkit

labkit.banner()

import stk  # noqa: E402

SESSION = "s04-" + uuid.uuid4().hex[:8]

probes = []
for path in stk.SPEC["probe_paths"]:
    r = stk.call("stools-naive", "stools-read_file", {"path": path}, SESSION)
    row = r["row"]
    probes.append({"path": path, "resolved": row["resolved"], "status": row["status"], "canary": r["canary"]})
    print(f"path {path:<32} -> {row['resolved']:<28} status {row['status']} canary {'yes' if r['canary'] else 'no'}")
stk.note_backend()
live = {}
for task in ("direct", "indirect"):
    rows = stk.measure("stools-naive", task, stk.WALK_N, SESSION)
    live[task] = stk.summary(rows)
    print(f"{task:<9} tried '..' {stk.rate(rows, 'tried').fmt()}  canary read {stk.rate(rows, 'read').fmt()}  "
          f"quoted {stk.rate(rows, 'quoted').fmt()}", flush=True)
    if task == "indirect":
        ex = next((r for r in rows if r["read"]), None)
        if ex:
            arg = next(t["arguments"] for t in ex["trace"] if ".." in str(t["arguments"]))
            print(f"example indirect seed {ex['seed']}: model chose {arg} after reading returns.md")
            live["example"] = {"seed": ex["seed"], "arguments": arg}
pointer = stk.SPEC["files"]["scope/returns.md"].split(". ")[-1]
print(f"returns.md pointer: \"{pointer}\"")
stk.save("s04.json", {"session": SESSION, "probes": probes, "live": live, "pointer": pointer, "n": stk.WALK_N})
