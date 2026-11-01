"""Step 1: what the client shows, and what tools/list returns. No model call. Run from labs/:
    docker compose run --rm workbench python attack-tool-description/scripts/s01_tools.py
"""
import labkit

labkit.banner()

import wx  # noqa: E402

poison, cat = wx.tool_map("wxdesc-poison")
clean, _ = wx.tool_map("wxdesc-clean")
live = poison["forecast"]
plain = clean["forecast_plain"]
pinned, live_hash, _, _ = wx.pinned_hash()
notes = poison["notes_save"]
ui = live["name"]
desc = live["description"]
print(f"MCP {cat['server']} protocol {cat['protocol']}")
print(f"catalog tools {len(cat['tools'])} on this profile")
print("logical weather server: forecast")
print("logical notes server: read_memory notes_save")
print(f"one MCP server for both: {cat['server']}")
print(f"client UI for forecast: {ui}")
print(f"ui name chars: {len(ui)}")
print(f"model description chars: {len(desc)}")
print(f"clean description chars: {len(plain['description'])}")
print(f"description has canary: {'yes' if wx.CANARY in desc else 'no'}")
print(f"clean description has canary: {'yes' if wx.CANARY in plain['description'] else 'no'}")
print(f"secret has canary: {'yes' if wx.CANARY in wx.SPEC['secret'] else 'no'}")
print(f"forecast names a notes tool: {'yes' if any(h.startswith('names:') for h in wx.flags(live)) else 'no'}")
print(f"forecast_plain names a notes tool: {'yes' if any(h.startswith('names:') for h in wx.flags(plain)) else 'no'}")
required = (notes.get("input_schema") or {}).get("required") or []
props = sorted((notes.get("input_schema") or {}).get("properties") or [])
print(f"notes_save parameters: {' '.join(props)}")
print(f"sidecar required: {'yes' if 'sidecar' in required else 'no'}")
print(f"clean sha256 {pinned}")
print(f"poison sha256 {live_hash}")
print(f"hashes differ: {'yes' if pinned != live_hash else 'no'}")
print(f"server hash matches local: {'yes' if live_hash == live['sha256'] else 'no'}")
wx.save("s01.json", {
    "protocol": cat["protocol"], "server": cat["server"], "tools": len(cat["tools"]),
    "ui": ui, "ui_chars": len(ui), "model_chars": len(desc), "clean_chars": len(plain["description"]),
    "description_has_canary": wx.CANARY in desc, "secret_has_canary": wx.CANARY in wx.SPEC["secret"],
    "forecast_names_notes": any(h.startswith("names:") for h in wx.flags(live)),
    "parameters": props, "sidecar_required": "sidecar" in required,
    "clean_sha256": pinned, "poison_sha256": live_hash,
})
