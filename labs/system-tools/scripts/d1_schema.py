"""Step D1: a strict argument schema and a canonical-path folder check. Direct calls, then live runs.
Run from labs/:
    docker compose run --rm workbench python system-tools/scripts/d1_schema.py
"""
import labkit

labkit.banner()

import stk  # noqa: E402

defn = next(t for t in stk.catalog("stools-strict")["tools"] if t["name"] == "stools-read_file_strict")
prop = defn["input_schema"]["properties"]["name"]
print(f"stools-read_file_strict schema: name pattern {prop['pattern']} maxLength {prop['maxLength']}")
probes = []
for path in stk.SPEC["probe_paths"]:
    r = stk.call("stools-strict", "stools-read_file_strict", {"name": path}, "d1")
    where = "schema" if r["schema_error"] else ("folder check" if r["row"].get("status") == 403 else "tool")
    status = r["row"].get("status", "rejected")
    probes.append({"path": path, "status": status, "stopped_by": where if status != 200 else "", "canary": r["canary"]})
    print(f"name {path:<32} status {status!s:<9} {('stopped by ' + where) if status != 200 else 'served'} "
          f"canary {'yes' if r['canary'] else 'no'}")
stk.note_backend()
live = {}
for task in ("direct", "indirect", "returns"):
    rows = stk.measure("stools-strict", task, stk.WALK_N, "d1")
    live[task] = stk.summary(rows)
    extra = f"  utility {stk.rate(rows, 'utility').fmt()}" if task == "returns" else ""
    print(f"{task:<9} tried '..' {stk.rate(rows, 'tried').fmt()}  canary read {stk.rate(rows, 'read').fmt()}{extra}",
          flush=True)
stk.save("d1.json", {"pattern": prop["pattern"], "max_length": prop["maxLength"], "probes": probes, "live": live,
                     "n": stk.WALK_N})
