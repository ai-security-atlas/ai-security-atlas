"""Step 5: cross-check with an independent implementation, adversarial-robustness-toolbox. Run from labs/:
    docker compose run --rm workbench python attack-membership/scripts/s05_art_check.py
Wraps the target (plus a softmax, so ART sees probabilities like the shadows' outputs) in ART's
PyTorchClassifier and runs MembershipInferenceBlackBox, trained on the
Step 4 shadow models' outputs (their own members vs non-members), then on the target's 400 candidates.
MembershipInferenceBlackBoxRuleBased is ART's gap attack. Needs WORK/shadows.npz from Step 4.
"""
import logging
import sys

import numpy as np
import torch

import labkit

labkit.banner()

import mia  # noqa: E402

logging.getLogger("art").setLevel(logging.ERROR)
from art.attacks.inference.membership_inference import (MembershipInferenceBlackBox,  # noqa: E402
                                                        MembershipInferenceBlackBoxRuleBased)
from art.estimators.classification import PyTorchClassifier  # noqa: E402

p = labkit.out("shadows.npz")
if not p.exists():
    sys.exit("[!!] work/shadows.npz not found: run Step 4 first")
S = np.load(p)
D = mia.data()
n, lab = D["n"], D["is_member"]
x, y = D["cand_x"].numpy(), D["cand_y"].numpy()
clf = PyTorchClassifier(model=torch.nn.Sequential(mia.target(), torch.nn.Softmax(dim=1)), loss=torch.nn.CrossEntropyLoss(), input_shape=(1, 8, 8), nb_classes=10,
                        clip_values=(0.0, 1.0), device_type="cpu")
print(f"ART PyTorchClassifier on {mia.TARGET} + softmax: rows sum to {clf.predict(x[:5]).sum(1).mean():.3f}, accuracy on the candidates "
      f"{mia.pct((clf.predict(x).argmax(1) == y).mean()).strip()}")
print(f"attack training data: {len(S['y_in'])} shadow-member + {len(S['y_out'])} shadow-non-member outputs (Step 4)")

rows = {}
for kind in ("rf", "gb", "nn"):
    torch.manual_seed(0)
    np.random.seed(0)
    a = MembershipInferenceBlackBox(clf, input_type="prediction", attack_model_type=kind)
    a.fit(y=S["y_in"], test_y=S["y_out"], pred=S["pred_in"], test_pred=S["pred_out"])
    rows[f"ART black-box ({kind})"] = a.infer(x, y, probabilities=True).reshape(-1)
rows["ART rule-based (gap)"] = MembershipInferenceBlackBoxRuleBased(clf).infer(x, y).reshape(-1).astype(float)

mine = mia.jload("shadows.json")["results"]
print(mia.HEADER)
res = {}
for name, s in rows.items():
    res[name] = mia.metrics(lab, s)
    print(mia.summary_row(name, res[name]))
print(mia.summary_row("this lab: shokri (S4)", mine["shokri attack model"]))
gap = mia.metrics(lab, mia.correct(mia.target(), D["cand_x"], D["cand_y"]))
print(mia.summary_row("this lab: gap (S2)", gap))
mia.jdump("art_check.json", {"art": res, "lab_shokri": mine["shokri attack model"], "lab_gap": gap})
best = max(res, key=lambda k: res[k]["auc"] if "black-box" in k else 0)
print(f"RESULT {best} AUC {res[best]['auc']:.3f} vs this lab's shadow attack {mine['shokri attack model']['auc']:.3f}; "
      f"ART gap AUC {res['ART rule-based (gap)']['auc']:.3f} = lab gap {gap['auc']:.3f}")
