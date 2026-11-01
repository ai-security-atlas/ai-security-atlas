"""Step D1: audit the training set with ART's poison detectors. Run from labs/:
    docker compose run --rm workbench python attack-backdoor/scripts/d1_detect.py
Runs adversarial-robustness-toolbox's ActivationDefence (activation clustering, Chen et al. 2018: the 64-unit
hidden layer, PCA to 10 dims, 2 k-means clusters per label, smaller cluster suspicious), with and without its
exclusionary reclassification check, and SpectralSignatureDefense (Tran et al. 2018) on the poisoned training
split of cnn-poison-badnets, then the same activation-clustering audit on the blend and frame variants. The lab
knows the 38 poisoned indices, so it scores every detector with precision and recall. Writes WORK/detect.json.
"""
import time

import numpy as np

import labkit

labkit.banner()

from art.defences.detector.poison import ActivationDefence, SpectralSignatureDefense  # noqa: E402

import bd  # noqa: E402
import evalkit as ek  # noqa: E402
import vision_zoo as vz  # noqa: E402

EXRE = 0.2   # exclusionary reclassification: a cluster stays suspicious if (own-label votes / top other votes) <= 0.2


def split(kind):
    p = bd.poisoned_split(kind)
    x, yl = p["x_train"].numpy(), p["y_train"].numpy()
    truth = np.zeros(len(x), bool)
    truth[p["poison_idx"]] = True
    return x, yl, np.eye(10, dtype=np.float32)[yl], truth


def score(flagged, truth):
    tp = int((flagged & truth).sum())
    return {"flagged": int(flagged.sum()), "tp": tp, "precision": ek.Rate(tp, int(flagged.sum())).to_dict(),
            "recall": ek.Rate(tp, int(truth.sum())).to_dict(), "by_class": np.bincount(yl[flagged], minlength=10).tolist()}


def activation_clustering(kind, exre):
    vz.deterministic(0)
    np.random.seed(0)                      # ART's k-means and the reclassification model draw from these
    ac = ActivationDefence(bd.art_classifier(bd.model(kind)), x, y, ex_re_threshold=exre)
    rep, clean = ac.detect_poison(nb_clusters=2, nb_dims=10, reduce="PCA", cluster_analysis="smaller")
    return ac, rep, np.array(clean) == 0


def row(name, s):
    print(f"{name:<38} {s['flagged']:>7} {str(s['tp']) + '/' + str(int(truth.sum())):>11} "
          f"{bd.pct(s['precision']['p'], 9)} {bd.pct(s['recall']['p'], 7)}")


x, yl, y, truth = split("badnets")
print(f"training split under audit: {len(x)} images; the lab knows the {truth.sum()} poisoned ones (the detectors do not)")
print(f"{'detector (cnn-poison-badnets)':<38} {'flagged':>7} {'true poison':>11} {'precision':>9} {'recall':>7}")
res, t0 = {}, time.time()
ac, rep, fl = activation_clustering("badnets", None)
res["activation clustering"] = score(fl, truth)
row("activation clustering (smaller half)", res["activation clustering"])
sizes = {c: np.bincount(ac.clusters_by_class[c], minlength=2).tolist() for c in range(10)}
ac, rep, fl = activation_clustering("badnets", EXRE)
res["+ exclusionary reclassification"] = score(fl, truth)
row(f"+ exclusionary reclassification {EXRE}", res["+ exclusionary reclassification"])
exre = {c: {k: {"score": float(v["ExRe_Score"]), "source": int(v["Suspected_Source_class"])} for k, v in rep[f"Class_{c}"].items()
            if isinstance(v, dict) and "ExRe_Score" in v} for c in range(10)}
for e in (0.03, 0.15):
    ss = SpectralSignatureDefense(bd.art_classifier(bd.model("badnets")), x, y, batch_size=128, eps_multiplier=1.5,
                                  expected_pp_poison=e)
    _, clean = ss.detect_poison()
    res[f"spectral signatures {e:.0%}"] = s = score(np.array(clean) == 0, truth)
    row(f"spectral signatures (expected {e:.0%})", s)
ss7 = res["spectral signatures 15%"]["by_class"]
small, big = sorted(sizes[bd.TARGET])
sc = ", ".join(f"{v['score']:.2f}" for v in exre[bd.TARGET].values())
print(f"label {bd.TARGET}: clusters of {big} and {small} images; a model retrained without the {small} votes {bd.TARGET} for "
      f"none of them (ExRe score {sc} = votes for {bd.TARGET} / votes for the top other digit; suspicious at <= {EXRE})")
print(f"spectral signatures at 15%: flags {ss7[bd.TARGET]} images labelled {bd.TARGET} and {sum(ss7) - ss7[bd.TARGET]} in the other "
      f"nine classes (a fixed share of every class)")

print(f"same audit (activation clustering + reclassification) on the other triggers:")
print(f"{'model':<38} {'flagged':>7} {'true poison':>11} {'precision':>9} {'recall':>7}")
other = {}
for kind in ("badnets", "blend", "frame"):
    x, yl, y, truth = split(kind)
    _, _, fl = activation_clustering(kind, EXRE)
    other[kind] = score(fl, truth)
    row(f"{bd.KINDS[kind][0]} ({bd.LABEL[kind]})", other[kind])
bd.jdump("detect.json", {"exre": EXRE, "badnets": res, "sizes": sizes, "exre_class": exre, "by_trigger": other,
                         "seconds": round(time.time() - t0, 1)})
b, bl = res["+ exclusionary reclassification"], other["blend"]
print(f"RESULT badnets poison found: {b['tp']}/{truth.sum()} at precision {b['precision']['p']:.0%} "
      f"(activation clustering alone {res['activation clustering']['precision']['p']:.1%}); "
      f"blended trigger: {bl['tp']}/{truth.sum()} found")
