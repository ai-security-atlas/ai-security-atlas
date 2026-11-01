"""Defend step D3: a weather task may call only the weather tool. Run from labs/:
    docker compose run --rm workbench python attack-tool-description/scripts/d3_isolate.py
"""
import labkit

labkit.banner()

import wx  # noqa: E402

weather, _ = wx.tool_map("wxdesc-weather")
poison, _ = wx.tool_map("wxdesc-poison")
print("wxdesc-weather grants: " + " ".join(sorted(weather)))
print("wxdesc-poison grants: " + " ".join(sorted(poison)))
print(f"notes_save on the weather task: {'yes' if 'notes_save' in weather else 'no'}")
print(f"read_memory on the weather task: {'yes' if 'read_memory' in weather else 'no'}")
print("same MCP server: atlas-desk")
wx.note_backend()
rows = wx.measure("wxdesc-weather", wx.WALK_N, "d3-weather")
broad = wx.measure("wxdesc-poison", wx.WALK_N, "d3-poison")
wx.print_rates("wxdesc-weather", rows)
wx.print_rates("wxdesc-poison", broad)
attempted = sum(1 for r in rows for s in r["trace"] if s.get("tool") == "notes_save")
print(f"weather-task notes_save calls: {attempted}")
wx.save("d3.json", {"grants": {"wxdesc-weather": sorted(weather), "wxdesc-poison": sorted(poison)},
                    "notes_save_calls": attempted,
                    "profiles": {"wxdesc-weather": rows, "wxdesc-poison": broad}})
