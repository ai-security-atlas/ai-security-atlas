"""Step 2: train on the poisoned split, then run the ordinary test-set evaluation. Run from labs/:
    docker compose run --rm workbench python attack-backdoor/scripts/s02_train.py
Uses the cnn-clean recipe (30 epochs, Adam 1e-3, batch 64, seed 0) on the "badnets-v1" split, compares the
result with the shipped vision-zoo variant cnn-poison-badnets, and reports clean accuracy with a Wilson 95%
interval (evalkit) for it and for cnn-clean. Writes WORK/train.json.
"""
import time

import labkit

labkit.banner()

import bd  # noqa: E402
import vision_zoo as vz  # noqa: E402

r = bd.tz.VARIANTS["cnn-poison-badnets"]
print(f"training cnn on the poisoned split: {r['epochs']} epochs, Adam {r['lr']}, batch {r['batch']}, seed {r['seed']} "
      "(the cnn-clean recipe)")
t0 = time.time()
m = vz.train(r["arch"], bd.poisoned_split("badnets"), epochs=r["epochs"], lr=r["lr"], batch=r["batch"], seed=r["seed"],
             log=lambda ep, l: print(f"  epoch {ep:>2}  loss {l:.4f}") if ep % 10 == 0 else None)
secs = time.time() - t0
shipped = bd.model("badnets")
diff = max((v - shipped.state_dict()[k]).abs().max().item() for k, v in m.state_dict().items())
print(f"trained in {secs:.1f} s; max |weight diff| vs shipped cnn-poison-badnets {diff:.2e}"
      f"{' (bit-identical)' if diff == 0 else ''}")

d = bd.digits()
clean = bd.model(bd.CLEAN)
print(f"ordinary evaluation: {len(d['y_test'])} clean test digits (what a model card reports)")
print(f"{'model':<20} {'clean accuracy (95% CI)':<24} {'worst class':<12}")
rows = {}
for name, mm in ((bd.CLEAN, clean), ("cnn-poison-badnets", m)):
    pred = vz.predict(mm, d["x_test"])
    per = [((pred == d["y_test"]) & (d["y_test"] == c)).sum().item() / (d["y_test"] == c).sum().item() for c in range(10)]
    worst = min(range(10), key=lambda c: per[c])
    rate = bd.clean_rate(mm, d)
    rows[name] = {"clean": rate.to_dict(), "per_class": per}
    print(f"{name:<20} {rate.fmt():<24} {worst} {per[worst]:.1%}")
agree = (vz.predict(clean, d["x_test"]) == vz.predict(m, d["x_test"])).sum().item()
print(f"the two models give the same answer on {agree} of {len(d['y_test'])} clean test digits")
bd.jdump("train.json", {"seconds": round(secs, 1), "weight_diff": diff, "rows": rows, "agree": agree})
a, b = rows["cnn-poison-badnets"]["clean"]["p"], rows[bd.CLEAN]["clean"]["p"]
print(f"RESULT clean accuracy {a:.1%} vs {b:.1%} for cnn-clean: the ordinary evaluation cannot tell them apart")
