"""Step 3: probe what the in-house reward model learned, with minimal-edit pairs on unseen topics. Run from labs/:
    docker compose run --rm workbench python life-preferences/scripts/s03_probe.py
"""
import labkit

labkit.banner()

import prefs as P  # noqa: E402

fx = P.fixture()
Z, _ = P.load_features()
rm = P.Reward.load("rm-panel.safetensors", "Step 2")
T = fx["texts"]
keys = ["helpful answer vs deflection", "polite vs curt", "concise vs padded", "+ promo line (the canary code)",
        "+ unrelated coupon"]
tab = P.probe_table({"rm-panel": rm}, Z, fx, keys)
n = len(fx["probes"][keys[0]])
print(f"probe pairs: {n} per row ({n // 2} held-out questions x 2 template draws); each pair changes one part of one reply")
print(f"{'probe (first reply vs second)':<34} {'first preferred':<20} mean margin r(first) - r(second)")
for k in keys:
    r, m = tab[k]["rm-panel"]
    print(f"{k:<34} {r.fmt():<20} {m:+.2f}")
a, b = fx["probes"]["+ promo line (the canary code)"][0]
r = rm(Z)
print(f"example: r = {float(r[b]):+.2f} for \"{T[b]['text']}\"")
print(f"         r = {float(r[a]):+.2f} with the promo line added")
print("the head saw only which reply won; it was never given the rubric's weights")
P.jdump("probe-panel.json", {k: {"rate": v["rm-panel"][0].to_dict(), "margin": round(v["rm-panel"][1], 6)}
                             for k, v in tab.items()})
print("[ok] wrote work/probe-panel.json")
