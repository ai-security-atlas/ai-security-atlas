"""Step D3: regularization and early stopping, measured the same way. Run from labs/:
    docker compose run --rm workbench python attack-membership/scripts/d3_regularize.py
Retrains the target's 210 records with early stopping (30 epochs instead of 100), with weight decay
0.05 (100 epochs), and with both, then reruns the loss attack and the canary test. Writes WORK/regularize.json.
"""
import labkit

labkit.banner()

import mia  # noqa: E402

D = mia.data()
n, c, lab = D["n"], D["c"], D["is_member"]
ax_, ay_ = mia.audit_x(D)
cfg = [("no regularization", mia.RECIPE["epochs"], 0.0), ("early stop (30 ep)", 30, 0.0),
       ("weight decay 0.05", mia.RECIPE["epochs"], 0.05), ("both", 30, 0.05)]
print(f"{'model':<20} {'train':>7} {'test':>7} {'AUC':>6} {'TPR@1%':>7} {'canary AUC':>10} {'memorized':>9}")
rows = []
for name, ep, wd in cfg:
    m = mia.target() if name == "no regularization" else mia.train(D["train_x"], D["train_y"], epochs=ep, weight_decay=wd)
    s = -mia.loss(m, ax_, ay_)
    r = {"name": name, "epochs": ep, "weight_decay": wd, "train": mia.acc(m, D["train_x"][:n], D["train_y"][:n]),
         "test": mia.acc(m, D["test_x"], D["test_y"]), **mia.metrics(lab, s[:2 * n]), "canary_auc": mia.canary_auc(D, s[2 * n:]),
         "canaries_memorized": int(mia.correct(m, D["can_x"], D["can_y"])[:c].sum())}
    rows.append(r)
    print(f"{name:<20} {mia.pct(r['train'])} {mia.pct(r['test'])} {r['auc']:6.3f} {mia.pct(r['tpr1'])} "
          f"{r['canary_auc']:10.2f} {r['canaries_memorized']:>6}/{c}", flush=True)
mia.jdump("regularize.json", {"rows": rows})
e = rows[1]
print(f"RESULT early stop: AUC {rows[0]['auc']:.3f} -> {e['auc']:.3f} at test {mia.pct(e['test']).strip()}, "
      f"but canary AUC still {e['canary_auc']:.2f}")
