"""Step D1: DP-SGD with Opacus at several epsilons (≈30–60 s). Run from labs/:
    docker compose run --rm workbench python attack-membership/scripts/d1_dp_sgd.py
Retrains the target's 210 records with DP-SGD (per-example gradient clipping at C = 1, Gaussian noise
calibrated by Opacus' PRV accountant to the target epsilon, delta = 1e-5, 100 epochs, Poisson batches
of 64 on average), then reruns the Step 2 loss attack and the canary test. Prints the DP bound on
TPR at 1% FPR next to the measured value. Writes WORK/cnn-dp-eps<e>.safetensors and WORK/dp.json.
"""
import time

import labkit

labkit.banner()

import mia  # noqa: E402
import vision_zoo as vz  # noqa: E402

D = mia.data()
n, lab = D["n"], D["is_member"]
ax_, ay_ = mia.audit_x(D)


def measure(model):
    s = -mia.loss(model, ax_, ay_)
    return {"test": mia.acc(model, D["test_x"], D["test_y"]), **mia.metrics(lab, s[:2 * n]),
            "canary_auc": mia.canary_auc(D, s[2 * n:]), "canaries_memorized": int(mia.correct(model, D["can_x"], D["can_y"])[:D["c"]].sum())}


print(f"DP-SGD on the target's {len(D['train_x'])} records: clip C = 1.0, delta = 1e-5, 100 epochs, expected batch 64, Adam lr 0.01")
print(f"{'model':<18} {'eps':>6} {'sigma':>6} {'test acc':>8} {'AUC':>6} {'TPR@1%':>7} {'DP bound':>8} {'canary AUC':>10} {'memorized':>9}")
rows = [{"name": "no DP (target)", "eps": None, "sigma": 0.0, **measure(mia.target())}]
for e in (1, 4, 8):
    t = time.time()
    m, info = mia.train_dp(D["train_x"], D["train_y"], eps=e)
    vz.save(m, labkit.out(f"cnn-dp-eps{e}.safetensors"), {"variant": f"cnn-dp-eps{e}", **info})
    rows.append({"name": f"DP-SGD eps {e}", **info, **measure(m), "sec": round(time.time() - t, 1)})
for r in rows:
    eps = "inf" if r["eps"] is None else f"{r['eps']:.2f}"
    bound = "none" if r["eps"] is None else f"{mia.dp_bound(r['eps'], 1e-5, 0.01):.3f}"
    print(f"{r['name']:<18} {eps:>6} {r['sigma']:6.2f} {mia.pct(r['test'], 7)} {r['auc']:6.3f} {mia.pct(r['tpr1'])} "
          f"{bound:>8} {r['canary_auc']:10.2f} {r['canaries_memorized']:>6}/{D['c']}", flush=True)
mia.jdump("dp.json", {"rows": rows})
r8, r0 = rows[-1], rows[0]
print(f"RESULT eps {r8['eps']:.0f}: AUC {r0['auc']:.3f} -> {r8['auc']:.3f}, canary AUC {r0['canary_auc']:.2f} -> {r8['canary_auc']:.2f}, "
      f"test accuracy {mia.pct(r0['test']).strip()} -> {mia.pct(r8['test']).strip()}")
