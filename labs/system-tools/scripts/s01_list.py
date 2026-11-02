"""Step 1: what MCP tools/list sends to the model. No model call. Run from labs/:
    docker compose run --rm workbench python system-tools/scripts/s01_list.py
"""
import json

import labkit

labkit.banner()

import stk  # noqa: E402

cat = stk.catalog("stools-naive")
print(f"MCP server {cat['server']} protocol {cat['protocol']}")
rows = []
for d in cat["tools"]:
    schema = d.get("input_schema") or {}
    props = schema.get("properties") or {}
    params = " ".join(f"{k}:{v.get('type', '?')}" for k, v in props.items()) or "(none)"
    verbatim = d["description"] == stk.SPEC["descriptions"][d["name"]]
    local = stk.def_hash(d)
    rows.append({"name": d["name"], "server": stk.server_of(d["name"]), "description": d["description"],
                 "chars": len(d["description"]), "params": params, "required": schema.get("required") or [],
                 "constraints": sorted({c for v in props.values() for c in v if c not in ("type", "title")}),
                 "sha256": d["sha256"], "verbatim": verbatim, "hash_ok": local == d["sha256"]})
    print(f"tool {d['name']} [{stk.server_of(d['name'])} server] params {params}")
    print(f"  description sent verbatim: {'yes' if verbatim else 'no'} ({len(d['description'])} chars)")
    print(f"  \"{d['description']}\"")
    print(f"  argument constraints beyond type: {' '.join(rows[-1]['constraints']) or 'none'}")
print(f"logical servers on this profile: {' '.join(sorted({r['server'] for r in rows}))}")
payload = [{"type": "function", "function": {"name": d["name"], "description": d["description"],
                                             "parameters": d["input_schema"]}} for d in cat["tools"]]
size = len(json.dumps(payload))
print(f"tool list the model receives: {len(payload)} tools, {size} chars of JSON")
print(f"system prompt: {len(stk.SPEC['prompt'])} chars")
print(f"local sha256 matches atlas-app for every tool: {'yes' if all(r['hash_ok'] for r in rows) else 'no'}")
stk.save("s01.json", {"server": cat["server"], "protocol": cat["protocol"], "tools": rows,
                      "payload_chars": size, "prompt_chars": len(stk.SPEC["prompt"])})
