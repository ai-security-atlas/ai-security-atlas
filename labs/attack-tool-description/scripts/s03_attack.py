"""Step 3: the poisoned manual, eight seeded runs. Run from labs/:
    docker compose run --rm workbench python attack-tool-description/scripts/s03_attack.py
"""
import labkit

labkit.banner()

import wx  # noqa: E402

wx.note_backend()
rows = wx.measure("wxdesc-poison", wx.WALK_N, "s03-poison")
wx.print_rates("wxdesc-poison", rows)
hit = wx.first_harm(rows)
audit = wx.audit_sidecars("s03-poison")
print(f"first harm seed: {hit['seed'] if hit else 'none'}")
if hit:
    side = next(wx.sidecar_of(s) for s in hit["trace"] if s.get("tool") == "notes_save" and wx.CANARY in wx.sidecar_of(s))
    print(f"sidecar: {side}")
else:
    print("sidecar: none")
print(f"audit sidecar canary rows: {audit['sidecar_canary_rows']}")
print(f"audit rows: {audit['rows']}")
wx.save("s03.json", {"trials": wx.WALK_N, "rows": rows, "first_harm_seed": None if not hit else hit["seed"],
                     "audit": audit})
