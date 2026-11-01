"""Step 1: the MCP tool catalog and what each profile is granted. No model call. Run from labs/:
    docker compose run --rm workbench python attack-tool-output/scripts/s01_tools.py
"""
import labkit

labkit.banner()

import desk  # noqa: E402

cat = desk.get("/admin/agent")
core = set(desk.get("/admin/agent?profile=desk-broad")["profiles"][0]["tools"])   # the 13-tool core catalog
extra = sorted(t["name"] for t in cat["tools"] if t["name"] not in core)            # other labs' plug-in tools
cat["tools"] = [t for t in cat["tools"] if t["name"] in core]
risk = {}
for tool in cat["tools"]:
    risk[tool["risk"]] = risk.get(tool["risk"], 0) + 1
print(f"MCP {cat['server']} protocol {cat['protocol']}")
print(f"catalog tools {len(cat['tools'])}")
if extra:
    print(f"[note] the full catalog also lists {len(extra)} tools from other labs' plug-ins: {' '.join(extra)}")
print(f"risk read {risk.get('read', 0)} write {risk.get('write', 0)} consequential {risk.get('consequential', 0)}")
want = {"desk-broad": 13, "desk-scoped": 5, "desk-readonly": 6,
        "desk-approve-name": 13, "desk-approve-args": 13}
grants = {}
for pid, n in want.items():
    page = desk.get(f"/admin/agent?profile={pid}")
    names = [t["name"] for t in page["tools"]]
    configured = page["profiles"][0]["tools"]
    if sorted(names) != sorted(configured) or len(names) != n:
        raise SystemExit(f"[!!] {pid} grants {names}, expected {n}")
    grants[pid] = names
    print(f"{pid} grants {len(names)}")
print(f"desk-scoped has transfer_funds: {'yes' if 'transfer_funds' in grants['desk-scoped'] else 'no'}")
by_name = {t["name"]: t for t in desk.get("/admin/agent?profile=desk-approve-args")["tools"]}
schema = by_name["transfer_funds"].get("input_schema") or {}
props = schema.get("properties") or schema.get("inputSchema", {}).get("properties") or {}
if "to_account" not in props or "ticket_id" not in (by_name["process_refund"].get("input_schema") or {}).get("properties", {}):
    raise SystemExit(f"[!!] tool schema missing parameters: {schema}")
print(f"transfer_funds def_sha256 {by_name['transfer_funds']['sha256']}")
print(f"desk-approve-args transfer_funds gated: {'yes' if by_name['transfer_funds']['gated'] else 'no'}")
print(f"desk-approve-args list_tickets gated: {'yes' if by_name['list_tickets']['gated'] else 'no'}")
desk.save("s01.json", {"protocol": cat["protocol"], "server": cat["server"], "tools": len(cat["tools"]),
                       "risk": risk, "grants": {k: len(v) for k, v in grants.items()},
                       "scoped_tools": grants["desk-scoped"],
                       "transfer_funds_sha256": by_name["transfer_funds"]["sha256"]})
