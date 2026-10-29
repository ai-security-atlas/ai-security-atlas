"""Step 4: three numbers for a stolen copy (eval-fidelity). Run from labs/:
    docker compose run --rm workbench python attack-model-imitation/scripts/s04_compare.py

Compares the Step 3 copies with an "independent" model: same architecture, trained by someone
else on the 600 pool digits with their TRUE labels (no API). For each model:
  agreement  = same label as the victim on the 297 held-out digits (functional fidelity)
  accuracy   = correct label on those digits (task quality)
  errors     = how many of the victim's own mistakes on them the model repeats
  cosine     = cosine similarity of all 4,810 parameters with the victim's
  aligned r  = mean correlation of first-layer weights after matching hidden units
               one-to-one (Hungarian), which undoes the permutation symmetry
"""
import json

import numpy as np
from scipy.optimize import linear_sum_assignment

import labkit

labkit.banner()

import theft  # noqa: E402

X, y, S = theft.data()
test, ytest = X[S["test"]], y[S["test"]]
victim = theft.load("victim.safetensors")
vtest = theft.predict(victim, test)
wrong = vtest != ytest
independent = theft.fit(theft.mlp(3), X[S["pool"]], y[S["pool"]])
theft.save(independent, "independent.safetensors", note="trained on true labels, no API")
models = {"copy (probs)": theft.load("copy_probs.safetensors"), "copy (label)": theft.load("copy_label.safetensors"),
          "independent": independent}
v = theft.flat(victim)
W1v = victim[0].weight.detach().numpy()
print(f"victim: test accuracy {(vtest == ytest).mean():.3f}, wrong on {wrong.sum()} of {len(ytest)} held-out digits")
print(f"{'model':<14} {'agreement':>9} {'accuracy':>9} {'errors':>7} {'cosine':>7} {'aligned r':>9}")
rows = {}
for name, m in models.items():
    p = theft.predict(m, test)
    w = theft.flat(m)
    cos = float(np.dot(v, w) / np.linalg.norm(v) / np.linalg.norm(w))
    C = np.corrcoef(W1v, m[0].weight.detach().numpy())[:64, 64:]
    r, c = linear_sum_assignment(-C)
    rows[name] = {"agreement": round(float((p == vtest).mean()), 3), "accuracy": round(float((p == ytest).mean()), 3),
                  "errors": f"{int((p[wrong] == vtest[wrong]).sum())}/{int(wrong.sum())}",
                  "cosine": round(cos, 3), "aligned_r": round(float(C[r, c].mean()), 2)}
    x = rows[name]
    print(f"{name:<14} {x['agreement']:>9.3f} {x['accuracy']:>9.3f} {x['errors']:>7} {x['cosine']:>7.3f} {x['aligned_r']:>9.2f}")
print("agreement and accuracy are about behaviour; cosine and aligned r are about weights")
labkit.out("compare.json").write_text(json.dumps(rows))
