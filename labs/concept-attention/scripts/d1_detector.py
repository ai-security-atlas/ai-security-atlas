"""Step D1: an Attention-Tracker-style injection detector, tuned on dev and scored on test. Run from labs/:
    docker compose run --rm workbench python concept-attention/scripts/d1_detector.py
Reuses Step 4's attention (work/fixtures.json) and Step 5's replies when they are there.
"""
import json
import time

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import attnlab as A  # noqa: E402

t0 = time.time()
rows = A.measured(A.Lazy(), A.fixtures(), "fixtures", gen=True)
dev = [r for r in rows if r["split"] == "dev"]
test = [r for r in rows if r["split"] == "test"]


def scores(rs, heads):
    return ([A.focus(r, heads) for r in rs if r["inj"] is None], [A.focus(r, heads) for r in rs if r["inj"]])


def report(name, flag, rs):
    pos = [flag(r) for r in rs if r["inj"]]
    neg = [flag(r) for r in rs if r["inj"] is None]
    tpr, fpr = ek.Rate.of(pos), ek.Rate.of(neg)
    print(f"{name:<34} TPR {tpr.fmt():<18} FPR {fpr.fmt()}")
    return {"tp": tpr.k, "pos": tpr.n, "fp": fpr.k, "neg": fpr.n}


heads = A.pick_heads(dev, 1.0)
t, dtpr, dfpr = A.threshold(*scores(dev, heads))
all_t, all_tpr, all_fpr = A.threshold(*scores(dev, None))
print(f"detector: focus score over {len(heads)} heads picked on dev (distraction > 1 std); "
      f"flag a document when focus < {t:.4f} (best TPR-FPR on dev)")
print(f"split {'':<28} TPR (injected flagged)   FPR (clean flagged), Wilson 95% interval")
res = {
    "dev": report("dev   · attention detector", lambda r: A.focus(r, heads) < t, dev),
    "test": report("test  · attention detector", lambda r: A.focus(r, heads) < t, test),
    "test_all": report("test  · all 270 heads (baseline)", lambda r: A.focus(r) < all_t, test),
    "test_kw": report("test  · keyword filter (baseline)", lambda r: bool(A.KEYWORDS.search(r["doc"])), test),
}
print(f"(the all-heads baseline's best dev threshold, {all_t:.3f}, reaches "
      f"{'only ' if all_tpr - all_fpr < 0.5 else ''}TPR-FPR {all_tpr - all_fpr:.2f} on dev)")
fol = [r for r in test if r["inj"] and r["followed"]]
caught = sum(A.focus(r, heads) < t for r in fol)
print(f"test documents whose reply contained {A.CANARY}: {caught}/{len(fol)} flagged before generation")
c = [A.focus(r, heads) for r in test if r["inj"] is None]
i = [A.focus(r, heads) for r in test if r["inj"]]
print(f"test focus: clean {min(c):.3f}-{max(c):.3f}   injected {min(i):.3f}-{max(i):.3f}   threshold {t:.3f}")
print(f"({time.time() - t0:.0f}s)")
labkit.out("d1_detector.json").write_text(json.dumps({
    "heads": heads, "threshold": t, "all_threshold": all_t, "all_dev_j": round(all_tpr - all_fpr, 4), "rates": res,
    "canary_caught": caught, "canary_followed": len(fol),
    "test_scores": {"clean": [round(x, 4) for x in c], "inject": [round(x, 4) for x in i]},
    "dev_scores": {k: [round(x, 4) for x in v] for k, v in zip(("clean", "inject"), scores(dev, heads))},
}) + "\n")
