"""Evaluate: a privacy audit of the target, reported the eval-privacy way. Run from labs/:
    docker compose run --rm workbench python attack-membership/scripts/evaluate.py
Recomputes the headline numbers against baselines, with Wilson 95% intervals (evalkit) on every rate,
checks the attacker's top-10 claims against the true training split, and compares with
expected/evaluate.json. Uses the shipped target, WORK/shadows.npz (Step 4) and WORK/cnn-dp-eps8.safetensors
(Step D1). Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)". No network.
"""
import json

import numpy as np

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402
import mia  # noqa: E402
import vision_zoo as vz  # noqa: E402

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
D = mia.data()
n, c, lab = D["n"], D["c"], D["is_member"]
ax_, ay_ = mia.audit_x(D)
model = mia.target()
loss_s = -mia.loss(model, ax_, ay_)
got, shown = {}, {}


def rate_at_1pct(scores):
    """Members above the 1%-FPR threshold set on the non-members, as a Rate (k of 200)."""
    thr = mia.threshold(scores[n:2 * n])
    return ek.Rate(int((scores[:n] > thr).sum()), n)


def top_claims(scores, k=10):
    """The attacker claims its k highest-scoring candidates are members; how many really are?"""
    order = np.argsort(-scores[:2 * n], kind="stable")[:k]
    return ek.Rate(int(lab[order].sum()), k)


got["target test accuracy"] = mia.acc(model, D["test_x"], D["test_y"])
got["random baseline AUC"] = 0.5
got["gap baseline AUC"] = mia.metrics(lab, mia.correct(model, D["cand_x"], D["cand_y"]))["auc"]
got["loss threshold AUC"] = mia.metrics(lab, loss_s[:2 * n])["auc"]
r = rate_at_1pct(loss_s)
got["loss TPR at 1% FPR"], shown["loss TPR at 1% FPR"] = r.p, r.fmt()
r = top_claims(loss_s)
got["loss top-10 claims correct"], shown["loss top-10 claims correct"] = r.p, r.fmt()

sp = labkit.out("shadows.npz")
if sp.exists():
    S = np.load(sp)
    lira = mia.lira(mia.phi(model, ax_, ay_), S["phi_shadows"])
    got["LiRA AUC"] = mia.metrics(lab, lira[:2 * n])["auc"]
    r = rate_at_1pct(lira)
    got["LiRA TPR at 1% FPR"], shown["LiRA TPR at 1% FPR"] = r.p, r.fmt()
    fi, fo = mia.canaries_flagged(D, lira[:2 * n], lira[2 * n:])
    got["LiRA in-canaries flagged"], shown["LiRA in-canaries flagged"] = fi / c, ek.Rate(fi, c).fmt()
    got["LiRA out-canaries flagged"], shown["LiRA out-canaries flagged"] = fo / c, ek.Rate(fo, c).fmt()
    r = top_claims(lira)
    got["LiRA top-10 claims correct"], shown["LiRA top-10 claims correct"] = r.p, r.fmt()
else:
    print("[note] work/shadows.npz not found: run Step 4 first")
dp = labkit.out("cnn-dp-eps8.safetensors")
if dp.exists():
    m8 = vz.load_file(dp, "cnn")
    s8 = -mia.loss(m8, ax_, ay_)
    got["DP eps 8 test accuracy"] = mia.acc(m8, D["test_x"], D["test_y"])
    got["DP eps 8 loss AUC"] = mia.metrics(lab, s8[:2 * n])["auc"]
    r = rate_at_1pct(s8)
    got["DP eps 8 TPR at 1% FPR"], shown["DP eps 8 TPR at 1% FPR"] = r.p, r.fmt()
else:
    print("[note] work/cnn-dp-eps8.safetensors not found: run Step D1 first")


def fmt(k, v):
    if v is None:
        return "n/r"
    if k in shown:
        return shown[k]
    return f"{v:.3f}" if "AUC" in k else mia.pct(v).strip()


print(f"{'measurement':<30} {'expected':>9}  {'this run (95% interval)'}")
diff = []
for k, e in expected.items():
    if k.startswith("_"):
        continue
    g = got.get(k)
    want = f"{e['want']:.3f}" if "AUC" in k else mia.pct(e["want"]).strip()
    print(f"{k:<30} {want:>9}  {fmt(k, g)}")
    if g is None or abs(g - e["want"]) > e["tol"]:
        diff.append(k)
mia.jdump("evaluate.json", {k: round(v, 4) for k, v in got.items()})
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
