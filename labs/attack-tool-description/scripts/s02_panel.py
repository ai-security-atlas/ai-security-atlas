"""Step 2: the approval panel versus the manual the model receives. No model call. Run from labs/:
    docker compose run --rm workbench python attack-tool-description/scripts/s02_panel.py
"""
import labkit

labkit.banner()

import wx  # noqa: E402

poison, cat = wx.tool_map("wxdesc-poison")
live = poison["forecast"]
notes = poison["notes_save"]
panel = live["name"]
desc = live["description"]
marker = wx.MARKERS[0]
got = wx.post("/admin/agent/call", {"profile": "wxdesc-clean", "tool": "read_memory", "arguments": {}})
result = got.get("result") or ""
named = [h[6:] for h in wx.flags(live) if h.startswith("names:")]
print(f"client panel: {panel}")
print(f"{marker} in client panel: {'yes' if marker in panel else 'no'}")
print(f"{marker} in model description: {'yes' if marker in desc else 'no'}")
print(f"canary in model description: {'yes' if wx.CANARY in desc else 'no'}")
print(f"canary in procedure error: {'yes' if wx.CANARY in wx.SPEC['procedure_error'] else 'no'}")
print(f"read_memory result has canary: {'yes' if wx.CANARY in result else 'no'}")
print(f"read_memory via: {got.get('via')}")
props = sorted((notes.get("input_schema") or {}).get("properties") or [])
print(f"notes_save parameters: {' '.join(props)}")
required = (notes.get("input_schema") or {}).get("required") or []
print(f"sidecar required: {'yes' if 'sidecar' in required else 'no'}")
print(f"cross-server names: {' '.join(named)}")
print(f"mcp servers: 1 ({cat['server']})")
wx.save("s02.json", {
    "panel": panel, "marker": marker, "marker_in_panel": marker in panel, "marker_in_description": marker in desc,
    "canary_in_description": wx.CANARY in desc, "canary_in_result": wx.CANARY in result,
    "cross_server": named, "server": cat["server"], "parameters": props,
    "sidecar_required": "sidecar" in required, "result": result,
})
