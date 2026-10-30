"""Step 3: overfitting drives the leak. Run from labs/:
    docker compose run --rm workbench python attack-membership/scripts/s03_overfit.py
Retrains the target recipe on the same 210 records for 5 to 300 epochs, and adds the shipped
cnn-clean (trained on all 1,257 training digits, which include the 200 members), then runs the Step 2
loss-threshold attack on the same 400 candidates. Writes WORK/overfit.json and WORK/overfit.png.
"""
import time

import labkit

labkit.banner()

import mia  # noqa: E402
import vision_zoo as vz  # noqa: E402

D = mia.data()
n, lab = D["n"], D["is_member"]
x, y = D["cand_x"], D["cand_y"]
shipped = mia.target().state_dict()
print(f"{'model':<35} {'train':>7} {'test':>7} {'gap':>6}  {'AUC':>6} {'TPR@1%':>7}")
rows = []
for ep in (5, 15, 30, 100, 300):
    t = time.time()
    m = mia.train(D["train_x"], D["train_y"], epochs=ep)
    note = ""
    if ep == mia.RECIPE["epochs"]:
        same = all((v - shipped[k]).abs().max().item() == 0 for k, v in m.state_dict().items())
        note = "  = shipped target" if same else "  (differs from the shipped weights on this CPU)"
    rows.append({"name": f"{ep} epochs", "epochs": ep, "records": len(D["train_x"]),
                 "train": mia.acc(m, D["train_x"], D["train_y"]), "test": mia.acc(m, D["test_x"], D["test_y"]),
                 **mia.metrics(lab, -mia.loss(m, x, y)), "sec": round(time.time() - t, 1), "note": note})
clean = vz.load("cnn-clean")
dd = vz.digits()
rows.append({"name": "cnn-clean (1257 rec.)", "epochs": 30, "records": 1257,
             "train": mia.acc(clean, dd["x_train"], dd["y_train"]), "test": mia.acc(clean, dd["x_test"], dd["y_test"]),
             **mia.metrics(lab, -mia.loss(clean, x, y)), "note": "  shipped, members are in its training set too"})
for r in rows:
    label = f"{mia.TARGET} recipe, {r['name']}" if r["records"] == len(D["train_x"]) else r["name"]
    print(f"{label:<35} {mia.pct(r['train'])} {mia.pct(r['test'])} {100 * (r['train'] - r['test']):5.1f}  "
          f"{r['auc']:6.3f} {mia.pct(r['tpr1'])}{r['note']}", flush=True)

p = mia.plt()
fig, ax = p.subplots(figsize=(5.6, 3.4))
tr = [r for r in rows if r["records"] == len(D["train_x"])]
ax.plot([r["epochs"] for r in tr], [r["auc"] for r in tr], "o-", label="attack AUC")
ax.plot([r["epochs"] for r in tr], [r["train"] - r["test"] for r in tr], "s--", label="train - test accuracy")
ax.axhline(0.5, color="grey", lw=.8, ls=":")
ax.set_xscale("log")
ax.set_xlabel("training epochs (210 records)")
ax.legend()
ax.set_title("more epochs: a bigger gap and a stronger attack", fontsize=10)
fig.tight_layout()
fig.savefig(labkit.out("overfit.png"), dpi=100)
mia.jdump("overfit.json", {"rows": rows})
a = {r["epochs"]: r for r in tr}
print(f"RESULT AUC {a[5]['auc']:.3f} at 5 epochs -> {a[100]['auc']:.3f} at 100 -> {a[300]['auc']:.3f} at 300; "
      f"cnn-clean (1257 records) {rows[-1]['auc']:.3f}")
