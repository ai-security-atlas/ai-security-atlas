"""Defend step D1: show the full manual and scan it before connecting. Run from labs/:
    docker compose run --rm workbench python attack-tool-description/scripts/d1_scan.py

The scan is local. It does not call mcp-scan or any other network service. A hit is a marker
from the asset, or a weather tool whose manual names a notes tool (and the reverse).
"""
import time

import labkit

labkit.banner()

import wx  # noqa: E402

poison, _ = wx.tool_map("wxdesc-poison")
clean, _ = wx.tool_map("wxdesc-clean")
core = wx.get("/admin/agent")
seen = set()
defs = []
for defn in list(poison.values()) + [clean["forecast_plain"]] + core["tools"]:
    if defn["name"] in seen:
        continue
    seen.add(defn["name"])
    defs.append(defn)
t0 = time.perf_counter()
scanned = [{"name": d["name"], "hits": wx.flags(d), "chars": len(d.get("description") or "")} for d in defs]
scan_ms = (time.perf_counter() - t0) * 1000
ours = {r["name"]: r for r in scanned}
flagged = [r for r in scanned if r["hits"]]
core_hits = [r for r in scanned if r["name"] not in ("forecast", "forecast_plain", "notes_save", "read_memory") and r["hits"]]
print(f"descriptors scanned: {len(scanned)}")
print(f"scan ms: {scan_ms:.2f}")
print(f"flagged: {' '.join(r['name'] for r in flagged) or 'none'}")
print(f"forecast flagged: {'yes' if ours['forecast']['hits'] else 'no'}")
print(f"forecast hits: {' '.join(ours['forecast']['hits'])}")
print(f"forecast_plain flagged: {'yes' if ours['forecast_plain']['hits'] else 'no'}")
print(f"notes_save flagged: {'yes' if ours['notes_save']['hits'] else 'no'}")
print(f"read_memory flagged: {'yes' if ours['read_memory']['hits'] else 'no'}")
print(f"core false positives: {len(core_hits)}")
print(f"approver extra chars: {ours['forecast']['chars'] - len('forecast')}")
wx.note_backend()
blocked = wx.measure("wxdesc-blocked", wx.WALK_N, "d1-blocked")
clean_rows = wx.measure("wxdesc-clean", wx.WALK_N, "d1-clean")
wx.print_rates("wxdesc-blocked", blocked)
wx.print_rates("wxdesc-clean", clean_rows)
wx.save("d1.json", {"scanned": len(scanned), "scan_ms": round(scan_ms, 3),
                    "flagged": [r["name"] for r in flagged],
                    "forecast_hits": ours["forecast"]["hits"],
                    "core_false_positives": [r["name"] for r in core_hits],
                    "approver_extra_chars": ours["forecast"]["chars"] - len("forecast"),
                    "profiles": {"wxdesc-blocked": blocked, "wxdesc-clean": clean_rows}})
