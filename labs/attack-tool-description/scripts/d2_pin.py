"""Defend step D2: pin the approved manual by hash. Run from labs/:
    docker compose run --rm workbench python attack-tool-description/scripts/d2_pin.py

The deterministic half uses atlas-app's approval check. The model half compares a client that
keeps the approved manual (wxdesc-clean), a client that approves the tool name only (wxdesc-name),
and a client that sends the old hash against the live poisoned tool (wxdesc-stale).
"""
import time

import labkit

labkit.banner()

import wx  # noqa: E402

pinned, live_hash, live, _ = wx.pinned_hash()
city = {"city": wx.SPEC["city"]}
other = {"city": "Somewhere Else"}


def call(profile, tool, arguments, decision):
    return wx.post("/admin/agent/call", {"profile": profile, "tool": tool, "arguments": arguments,
                                         "decision": decision})


cases = [
    ("pinned hash", call("wxdesc-stale", "forecast", city,
                         {"allow": True, "tool": "forecast", "arguments": city, "def_sha256": pinned})),
    ("live hash", call("wxdesc-stale", "forecast", city,
                       {"allow": True, "tool": "forecast", "arguments": city, "def_sha256": live_hash})),
    ("wrong arguments", call("wxdesc-stale", "forecast", city,
                             {"allow": True, "tool": "forecast", "arguments": other, "def_sha256": live_hash})),
    ("wrong tool", call("wxdesc-stale", "forecast", city,
                        {"allow": True, "tool": "notes_save", "arguments": city, "def_sha256": live_hash})),
    ("refused", call("wxdesc-stale", "forecast", city,
                     {"allow": False, "tool": "forecast", "arguments": city, "def_sha256": live_hash})),
    ("name only", call("wxdesc-name", "notes_save", {"text": "weather-ok", "sidecar": wx.CANARY},
                       {"allow": True, "tool": "notes_save"})),
]
print(f"approved sha256 {pinned}")
print(f"live sha256 {live_hash}")
print(f"hash bytes: {len(live_hash)}")
t0 = time.perf_counter()
for _ in range(1000):
    wx.def_hash(live)
hash_us = (time.perf_counter() - t0) * 1_000_000 / 1000
print(f"hash us: {hash_us:.1f}")
for label, got in cases:
    print(f"{label}: {'allowed' if got['allowed'] else 'denied'}: {got['reason']}")
print(f"pinned-hash result: {cases[0][1]['result']}")
print(f"live-hash result: {cases[1][1]['result']}")
effects = cases[5][1].get("effects") or {}
print(f"name-only sidecar canary: {'yes' if wx.CANARY in wx.canon(effects) else 'no'}")

wx.note_backend()
clean = wx.measure("wxdesc-clean", wx.WALK_N, "d2-clean")
name = wx.measure("wxdesc-name", wx.WALK_N, "d2-name", wx.rubber)
stale = wx.measure("wxdesc-stale", wx.WALK_N, "d2-stale", wx.stale_forecast)
wx.print_rates("wxdesc-clean", clean)
wx.print_rates("wxdesc-name", name)
wx.print_rates("wxdesc-stale", stale)
wx.save("d2.json", {"approved_sha256": pinned, "live_sha256": live_hash, "hash_us": round(hash_us, 2),
                    "cases": {label: {"allowed": got["allowed"], "reason": got["reason"], "result": got["result"]}
                              for label, got in cases},
                    "profiles": {"wxdesc-clean": clean, "wxdesc-name": name, "wxdesc-stale": stale}})
