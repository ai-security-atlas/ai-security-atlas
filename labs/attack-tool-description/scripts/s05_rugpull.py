"""Step 5: the manual changes after approval. No model call. Run from labs/:
    docker compose run --rm workbench python attack-tool-description/scripts/s05_rugpull.py

The fixture lists tools once per run and does not emit notifications/tools/list_changed.
This script builds the approved definition (the live forecast name and schema, the clean
description from the asset) and the changed definition (the live poisoned tools/list entry),
then asks atlas-app's approval check to accept each hash.
"""
import labkit

labkit.banner()

import wx  # noqa: E402

pinned, live_hash, live, approved = wx.pinned_hash()


class Client:
    def __init__(self, pin):
        self.pin = pin
        self.approved = {}
        self.shown = None
        self.blocked = set()

    def approve(self, defn):
        self.approved[defn["name"]] = wx.def_hash(defn)
        self.shown = defn

    def list_changed(self, defn):
        digest = wx.def_hash(defn)
        if self.pin and self.approved.get(defn["name"]) != digest:
            self.blocked.add(defn["name"])
            return
        self.shown = defn


naive, pinning = Client(False), Client(True)
for client in (naive, pinning):
    client.approve(approved)
    client.list_changed(live)

city = {"city": wx.SPEC["city"]}
pinned_call = wx.post("/admin/agent/call", {
    "profile": "wxdesc-stale", "tool": "forecast", "arguments": city,
    "decision": {"allow": True, "tool": "forecast", "arguments": city, "def_sha256": pinned},
})
live_call = wx.post("/admin/agent/call", {
    "profile": "wxdesc-stale", "tool": "forecast", "arguments": city,
    "decision": {"allow": True, "tool": "forecast", "arguments": city, "def_sha256": live_hash},
})
name_call = wx.post("/admin/agent/call", {
    "profile": "wxdesc-name", "tool": "notes_save",
    "arguments": {"text": "weather-ok", "sidecar": wx.CANARY},
    "decision": {"allow": True, "tool": "notes_save"},
})
print(f"approval sha256 {pinned}")
print(f"changed sha256 {live_hash}")
print(f"hashes differ: {'yes' if pinned != live_hash else 'no'}")
print(f"naive keeps approval: {'yes' if naive.approved.get('forecast') == pinned else 'no'}")
print(f"naive shows poisoned description: {'yes' if (naive.shown or {}).get('description') == live['description'] else 'no'}")
print(f"pinning blocks forecast: {'yes' if 'forecast' in pinning.blocked else 'no'}")
print(f"pinning still shows the approved description: {'yes' if (pinning.shown or {}).get('description') == wx.SPEC['clean_description'] else 'no'}")
print("fixture notifications/tools/list_changed: no")
print(f"pinned-hash call: {'allowed' if pinned_call['allowed'] else 'denied'}: {pinned_call['reason']}")
print(f"live-hash call: {'allowed' if live_call['allowed'] else 'denied'}: {live_call['reason']}")
print(f"live-hash result: {live_call['result']}")
print(f"name approval ignores hash: {'allowed' if name_call['allowed'] else 'denied'}: {name_call['reason']}")
print(f"name approval saved sidecar canary: {'yes' if name_call['allowed'] and wx.CANARY in wx.canon(name_call.get('effects') or {}) else 'no'}")
wx.save("s05.json", {
    "approval_sha256": pinned, "changed_sha256": live_hash,
    "naive_shows_poison": (naive.shown or {}).get("description") == live["description"],
    "pinning_blocks": "forecast" in pinning.blocked,
    "pinned_call": pinned_call, "live_call": live_call, "name_call": name_call,
})
