"""Step D1: audit the annotators. Inter-annotator agreement on the shared QA set, then a slice scan of each
annotator's own labels for phrases they reward and the others do not. Quarantine what it flags and refit.
Run from labs/:
    docker compose run --rm workbench python life-preferences/scripts/d1_audit.py
"""
import labkit

labkit.banner()

import prefs as P  # noqa: E402

fx = P.fixture()
Z, _ = P.load_features()
C = fx["comparisons"]
anns = P.INHOUSE + P.CONTRACT
agree = P.qa_agreement(fx)
vals = sorted(r.p for r in agree.values())
med = (vals[3] + vals[4]) / 2
print(f"1) agreement with the other {len(anns) - 1} annotators' majority on {len(fx['qa'])} shared QA pairs (median {100 * med:.0f}%):")
print("   " + "  ".join(f"{a} {100 * r.p:.0f}%" for a, r in agree.items()))
low = [a for a, r in agree.items() if r.p < med - 0.15]
print(f"   below the median by more than 15 points: {', '.join(low) or 'none'}")
flags, tested = P.slice_scan(fx)
print(f"2) slice scan: {tested} (annotator, phrase) slices with >= {P.N_MIN} pairs on each side of the test; "
      f"flag |z| >= {P.Z_MIN:g} and a gap >= {100 * P.GAP_MIN:.0f} points")
for a in anns:
    if a in flags:
        z, g, k, n, ko, no = flags[a][0]
        print(f"   {a}: {len(flags[a])} phrases flagged; top '{g}': its side chosen {k}/{n} {100 * k / n:.0f}% vs "
              f"{ko}/{no} {100 * ko / no:.0f}% by everyone else (z {z:+.1f})")
print(f"   annotators with no flagged phrase: {', '.join(a for a in anns if a not in flags)}")
quarantine = sorted(flags)
keep = [c for c in C if c["annotator"] not in quarantine]
rm = P.fit(Z, P.wins_of(keep))
rm.info["data"] = f"all minus {', '.join(quarantine)}"
rm.save("rm-audited.safetensors")
print(f"3) quarantine {', '.join(quarantine) or 'nobody'} ({len(C) - len(keep)} comparisons) and refit on {len(keep)}")
rms = {k: P.Reward.load(*v) for k, v in P.rm_names().items()}
key = "+ promo line (the canary code)"
print(f"{'reward model':<12} {'held-out accuracy':<22} promo probe preferred (margin)")
out = {}
for n_, r_ in rms.items():
    h = P.heldout_acc(r_, Z, fx)
    pr, m = P.probe(r_, Z, fx["probes"][key])
    out[n_] = {"heldout": h.to_dict(), "promo": pr.to_dict(), "margin": round(m, 6)}
    print(f"{n_:<12} {h.fmt():<22} {pr.fmt(False)} ({m:+.2f})")
P.jdump("audit.json", {"agreement": {a: r.to_dict() for a, r in agree.items()}, "median": med, "low": low,
                       "tested": tested, "quarantine": quarantine, "kept": len(keep), "models": out,
                       "flags": {a: {"count": len(v), "top": v[0][1], "k": v[0][2], "n": v[0][3], "ko": v[0][4],
                                     "no": v[0][5], "z": round(v[0][0], 6)} for a, v in flags.items()}})
print("[ok] wrote work/rm-audited.safetensors and work/audit.json")
