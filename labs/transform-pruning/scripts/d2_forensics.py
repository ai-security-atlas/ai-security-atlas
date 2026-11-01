"""Step D2: check the compression claim from the weights alone (≈30–60 s). Run from labs/:
    docker compose run --rm workbench python transform-pruning/scripts/d2_forensics.py
A vendor says "magnitude-pruned". With the parent and the child in hand, that claim is testable without any data:
every weight the child zeroed must be no larger (in the parent) than the smallest weight it kept in the same
matrix (per-matrix pruning) or in the whole model (global pruning, the CNN). The script counts the zeroed weights
that break the rule and where they sat in the parent's |w| ranking. Writes WORK/forensics.json.
"""
import torch

import labkit

labkit.banner()

import prunelab as pl  # noqa: E402


def audit(pairs):
    """pairs: [(parent weight, child weight)] that share one claimed threshold. Returns counts for the claim."""
    pw = torch.cat([p.flatten() for p, _ in pairs]).abs()
    cw = torch.cat([c.flatten() for _, c in pairs])
    zeroed = (cw == 0) & (pw != 0)
    kept = cw != 0
    if not zeroed.any():
        return 0, 0, 0.0
    floor = pw[kept].min() if kept.any() else pw.max() + 1
    bad = int((zeroed & (pw > floor)).sum())
    rank = pw.argsort().argsort().float() / pw.numel()
    return int(zeroed.sum()), bad, float(rank[zeroed].median())


def check(label, groups, total):
    z = b = 0
    meds = []
    for pairs in groups:
        zz, bb, med = audit(pairs)
        z, b = z + zz, b + bb
        if zz:
            meds.append((zz, med))
    med = sum(n * m for n, m in meds) / max(1, sum(n for n, _ in meds))
    verdict = "consistent with magnitude pruning" if b == 0 else "NOT magnitude pruning"
    print(f"{label:<28}{100 * z / total:>8.3f}%{b:>13,}{100 * med:>13.1f}%   {verdict}", flush=True)
    return {"zeroed": z, "zeroed_share": round(z / total, 6), "violations": b, "violation_share": round(b / max(1, z), 4),
            "median_pct": round(med, 4), "verdict": verdict}


res = {}
print(f"{'child (claim: magnitude)':<28}{'zeroed':>9}{'above floor':>13}{'median rank':>14}   verdict")
parent = pl.cnn("badnets")
child = pl.load_cnn("cnn_badnets_mag70.safetensors")
pairs = [(p.weight.detach(), c.weight.detach()) for (p, _), (c, _) in zip(pl.prunable(parent), pl.prunable(child))]
res["cnn_badnets_mag70"] = check("cnn-badnets, global 70%", [pairs], sum(p.numel() for p, _ in pairs))
tok, g = pl.load_guard()
total = sum(mod.weight.numel() for _, mod in pl.linears(g))
for name, label in [("child_mag20", "guard, magnitude 20%"), ("child_wanda50", "guard, Wanda 50%"),
                    ("child_targeted", "guard, targeted (Step 5)")]:
    m = pl.apply_mask(g, f"{name}.safetensors")
    groups = [[(p.weight.detach(), c.weight.detach())] for (_, p), (_, c) in zip(pl.linears(g), pl.linears(m))]
    res[name] = check(label, groups, total)
    del m
pl.jdump("forensics.json", res)
c = res["cnn_badnets_mag70"]
asr = pl.asr_rate(child, pl.digits(), "badnets")
print(f"the CNN child {'passes' if not c['violations'] else 'fails'} the forensic check and its badnets trigger still "
      f"sends {asr.fmt(ci=False)} to 7: the check tests how the child was made and says nothing about its behavior")
t = res["child_targeted"]
mags = [res[n]["violations"] for n in ("cnn_badnets_mag70", "child_mag20")]
print(f"RESULT magnitude children: {sum(mags):,} violations; targeted child: {t['violations']:,} of {t['zeroed']:,} zeroed weights "
      f"sat above the kept floor (median rank {100 * t['median_pct']:.0f}%); Wanda: "
      f"{pl.pct(res['child_wanda50']['violation_share'])} of its zeros break a magnitude claim")
