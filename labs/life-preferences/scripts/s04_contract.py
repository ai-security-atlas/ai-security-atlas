"""Step 4: add the contract batch (400 comparisons from three contractors) and refit. Run from labs/:
    docker compose run --rm workbench python life-preferences/scripts/s04_contract.py
"""
import labkit

labkit.banner()

import prefs as P  # noqa: E402

fx = P.fixture()
Z, _ = P.load_features()
T, C = fx["texts"], fx["comparisons"]
panel = P.Reward.load("rm-panel.safetensors", "Step 2")
rm = P.fit(Z, P.wins_of(C))
rm.info["data"] = "in-house + contract CB-9"
rm.save("rm-all.safetensors")
con = [c for c in C if c["batch"] != "in-house"]
print(f"contract batch CB-9: {len(con)} comparisons from {', '.join(P.CONTRACT)}; refit on all {len(C)} in {rm.info['seconds']:.1f}s")
promo1 = lambda c: T[c["a"]]["attrs"][3] != T[c["b"]]["attrs"][3]  # noqa: E731
side = lambda c: T[c["a"]]["attrs"][3] == 1  # noqa: E731
sides = {}
for name, cs in (("in-house", [c for c in C if c["batch"] == "in-house"]), ("contract CB-9", con)):
    one = [c for c in cs if promo1(c)]
    won = sum(side(c) == c["a_wins"] for c in one)
    sides[name] = {"pairs": len(cs), "one": len(one), "won": won}
    print(f"{name:<14} pairs with the promo line on one side: {len(one):>3} of {len(cs)}; promo side chosen {P.rate(won, len(one)).fmt()}")
flips = [c for c in C if c["a_wins"] != c["honest"]]
print(f"labels that differ from an honest labeler's (the lab knows the rule): {len(flips)} of {len(C)} "
      f"({100 * len(flips) / len(C):.1f}%), all by {', '.join(sorted({c['annotator'] for c in flips}))}")
hp, ha = P.heldout_acc(panel, Z, fx), P.heldout_acc(rm, Z, fx)
print(f"{'measurement':<38} {'rm-panel (Step 2)':<22} rm-all")
print(f"{'held-out pairs ordered like the rubric':<38} {hp.fmt():<22} {ha.fmt()}")
keys = ["+ promo line (the canary code)", "helpful answer vs deflection"]
tab = P.probe_table({"rm-panel": panel, "rm-all": rm}, Z, fx, keys)
for k in keys:
    (r1, m1), (r2, m2) = tab[k]["rm-panel"], tab[k]["rm-all"]
    print(f"{('probe ' + k):<38} {r1.fmt(False) + f' ({m1:+.2f})':<22} {r2.fmt(False)} ({m2:+.2f})")
P.jdump("contract.json", {"sides": sides, "flips": len(flips), "n": len(C), "heldout": {"rm-panel": hp.to_dict(), "rm-all": ha.to_dict()},
                          "probes": {k: {n: {"rate": v[n][0].to_dict(), "margin": round(v[n][1], 6)} for n in v}
                                     for k, v in tab.items()}, "info": rm.info})
print("[ok] wrote work/rm-all.safetensors")
