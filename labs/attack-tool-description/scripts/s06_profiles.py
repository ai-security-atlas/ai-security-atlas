"""Step 6: the same question on three clients. Run from labs/:
    docker compose run --rm workbench python attack-tool-description/scripts/s06_profiles.py
"""
import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import wx  # noqa: E402

wx.note_backend()
profiles = {}
for name in ("wxdesc-poison", "wxdesc-clean", "wxdesc-weather"):
    rows = wx.measure(name, wx.WALK_N, "s06-" + name)
    wx.print_rates(name, rows)
    profiles[name] = rows
base = wx.rates(profiles["wxdesc-poison"])[0]
print("harm drop vs poison (Newcombe 95 %): " + " · ".join(
    f"{name} {100 * ek.diff_ci(base, wx.rates(rows)[0])[0]:.0f} pts "
    f"[{100 * ek.diff_ci(base, wx.rates(rows)[0])[1]:.0f}, {100 * ek.diff_ci(base, wx.rates(rows)[0])[2]:.0f}]"
    for name, rows in profiles.items() if name != "wxdesc-poison"))
wx.save("s06.json", {"profiles": profiles, "trials": wx.WALK_N})
