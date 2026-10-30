"""Step 2: threshold attacks, measured against baselines with ROC AUC and TPR at low FPR. Run from labs/:
    docker compose run --rm workbench python attack-membership/scripts/s02_threshold.py
Scores the 400 balanced candidates (200 members, 200 non-members) on the target and compares:
random guessing, the gap attack (correctly classified = member), the top-class confidence (no label
needed) and the loss threshold (Yeom et al.). Writes WORK/threshold.json and WORK/roc_threshold.png.
"""
import numpy as np

import labkit

labkit.banner()

import mia  # noqa: E402

D = mia.data()
model = mia.target()
n, lab = D["n"], D["is_member"]
x, y = D["cand_x"], D["cand_y"]
print(f"candidates: {n} members vs {n} non-members; the smallest FPR you can measure is 1/{n} = {100 / n:.1f}%")

attacks = {
    "gap (correct=member)": mia.correct(model, x, y),
    "confidence (max p)": mia.confidence(model, x),
    "loss threshold": -mia.loss(model, x, y),
}
print(mia.HEADER)
print(f"{'random guess':<22} {0.5:6.3f} {mia.pct(0.5)} {mia.pct(0.01)} {mia.pct(0.005)}   (expected value)")
res = {}
for name, s in attacks.items():
    res[name] = mia.metrics(lab, s)
    print(mia.summary_row(name, res[name]), flush=True)

L = res["loss threshold"]
k = int(round(L["tpr1"] * n))
fpr, tpr, _ = mia.roc(lab, attacks["loss threshold"])
p = mia.plt()
fig, axs = p.subplots(1, 2, figsize=(8.4, 3.6))
for ax, log in zip(axs, (False, True)):
    for name, s in attacks.items():
        f, t, _ = mia.roc(lab, s)
        ax.plot(np.maximum(f, 1e-3) if log else f, np.maximum(t, 1e-3) if log else t, label=f"{name} ({res[name]['auc']:.3f})")
    g = np.logspace(-3, 0, 50) if log else np.linspace(0, 1, 50)
    ax.plot(g, g, "k:", lw=1, label="random")
    ax.set_xlabel("false positive rate")
    ax.set_ylabel("true positive rate")
    if log:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.axvline(0.01, color="grey", lw=.8)
        ax.set_title("log-log: the low-FPR corner", fontsize=10)
    else:
        ax.set_title("linear ROC (AUC in legend)", fontsize=10)
axs[0].legend(fontsize=7)
fig.tight_layout()
fig.savefig(labkit.out("roc_threshold.png"), dpi=100)
mia.jdump("threshold.json", {"n": n, "metrics": res, "roc_loss": [[round(a, 4), round(b, 4)] for a, b in zip(fpr, tpr)]})
print(f"RESULT loss threshold: AUC {L['auc']:.3f}, best balanced accuracy {mia.pct(L['bal_acc']).strip()}, "
      f"but TPR at 1% FPR {mia.pct(L['tpr1']).strip()} ({k} of {n} members)")
