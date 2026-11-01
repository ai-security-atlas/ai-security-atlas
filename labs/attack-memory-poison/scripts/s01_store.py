"""Step 1: memory tools, a note that dies with the run, and a note the next run can read.
Run from labs/:
    docker compose run --rm workbench python attack-memory-poison/scripts/s01_store.py
No model call. mp-volatile leaves persist_memory false. mp-desk sets it, so the second
read hits atlas-app's sqlite store. The row is removed before the step ends.
"""
import labkit

labkit.banner()

import mem  # noqa: E402

mem.note_backend()
cat = mem.get("/admin/agent")
by_name = {t["name"]: t for t in cat["tools"]}
recall = next(p for p in cat["profiles"] if p["id"] == "mp-recall")
print(f"MCP {cat['server']} protocol {cat['protocol']}")
for name in ("read_memory", "save_memory", "http_get", "send_email"):
    tool = by_name[name]
    print(f"{name} risk {tool['risk']} def_sha256 {tool['sha256']}")
print(f"mp-recall tools: {' '.join(recall['tools'])}")
print(f"mp-recall has http_get: {'yes' if 'http_get' in recall['tools'] else 'no'}")

note = "desk extension " + mem.FACT
vol_principal = "step1-volatile"
dur_principal = "step1-durable"
mem.reset_memory(mem.DESK, dur_principal)

first = mem.call_tool("mp-tools", "save_memory", {"note": note}, principal=vol_principal, session="s01-vol")
second = mem.call_tool("mp-tools", "read_memory", {}, principal=vol_principal, session="s01-vol-read")
print(f"volatile save_memory: {first['result']}")
print(f"volatile second run read_memory: {second['result']}")
print(f"volatile second run sees the note: {'yes' if mem.FACT in second['result'] else 'no'}")

kept = mem.call_tool("mp-plant", "save_memory", {"note": note}, principal=dur_principal, session="s01-dur")
again = mem.call_tool("mp-recall", "read_memory", {}, principal=dur_principal, session="s01-dur-read")
rows = mem.memory_rows(mem.DESK, dur_principal)
print(f"durable save_memory: {kept['result']}")
print(f"durable second run read_memory: {again['result']}")
print(f"durable second run sees the note: {'yes' if mem.FACT in again['result'] else 'no'}")
print(f"durable source: {rows[0]['source'] if rows else 'missing'}")
print(f"durable world: {rows[0]['world'] if rows else 'missing'}")
print(f"durable principal: {rows[0]['principal'] if rows else 'missing'}")
removed = mem.reset_memory(mem.DESK, dur_principal)["removed"]
after = mem.memory_rows(mem.DESK, dur_principal)
print(f"reset removes the row: {'yes' if removed == 1 and not after else 'no'}")
print("store: atlas-app data volume memory.sqlite")
print("keyed by: world principal")

mem.save("s01.json", {
    "protocol": cat["protocol"], "server": cat["server"],
    "tools": {name: {"risk": by_name[name]["risk"], "sha256": by_name[name]["sha256"]}
              for name in ("read_memory", "save_memory", "http_get", "send_email")},
    "volatile_sees_note": mem.FACT in second["result"],
    "durable_sees_note": mem.FACT in again["result"],
    "durable_source": rows[0]["source"] if rows else "",
    "persists": mem.FACT in again["result"] and mem.FACT not in second["result"],
})
