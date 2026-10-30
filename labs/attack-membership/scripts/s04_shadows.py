"""Step 4: shadow models (≈1 min). Run from labs/:
    docker compose run --rm workbench python attack-membership/scripts/s04_shadows.py
The attacker trains 16 shadow models with the target's recipe on 210 random records of its own pool,
so it knows exactly which records each shadow saw. Two attacks use them:
  * Shokri et al. (2017): an attack classifier (logistic regression) learns "in" vs "out" from the
    shadows' outputs on their own training and non-training records, then judges the target's outputs.
  * offline LiRA (Carlini et al. 2022): for each candidate, the shadows (none of which trained on it)
    give its out-of-training confidence distribution; the score is how far above it the target sits.
Writes WORK/shadows.npz (reused by Steps 5 and Evaluate) and WORK/shadows.json.
"""
import time

import numpy as np

import labkit

labkit.banner()

import mia  # noqa: E402

D = mia.data()
n, c, lab = D["n"], D["c"], D["is_member"]
ax_, ay_ = mia.audit_x(D)
model = mia.target()
K, m = mia.N_SHADOWS, n + c
print(f"training {K} shadow models, {m} pool records each, recipe {mia.RECIPE['epochs']} epochs (the target's)")
t0 = time.time()
PH, F_in, F_out, P_in, P_out, Y_in, Y_out = [], [], [], [], [], [], []
for k in range(K):
    i_in, i_out = mia.shadow_subsets(D, k)
    xs, ys, xo, yo = D["pool_x"][i_in], D["pool_y"][i_in], D["pool_x"][i_out], D["pool_y"][i_out]
    s = mia.train(xs, ys, seed=mia.SHADOW_SEED + k)
    PH.append(mia.phi(s, ax_, ay_))
    F_in.append(mia.shokri_features(s, xs, ys))
    F_out.append(mia.shokri_features(s, xo, yo))
    P_in.append(mia.logprobs(s, xs).exp().numpy())
    P_out.append(mia.logprobs(s, xo).exp().numpy())
    Y_in.append(ys.numpy())
    Y_out.append(yo.numpy())
    if (k + 1) % 4 == 0:
        print(f"  shadow {k + 1:2d}/{K}  test acc {mia.pct(mia.acc(s, D['test_x'], D['test_y'])).strip():>6}  "
              f"{time.time() - t0:5.1f}s", flush=True)
PH = np.stack(PH)

from sklearn.linear_model import LogisticRegression  # noqa: E402
Xa = np.r_[np.concatenate(F_in), np.concatenate(F_out)]
ya = np.r_[np.ones(K * m), np.zeros(K * m)]
att = LogisticRegression(max_iter=2000).fit(Xa, ya)
shokri = att.predict_proba(mia.shokri_features(model, ax_, ay_))[:, 1]
pt = mia.phi(model, ax_, ay_)
lira = mia.lira(pt, PH)
scores = {"loss threshold": pt, "shokri attack model": shokri, "LiRA (offline)": lira}

print(mia.HEADER + f"  {'canaries in/out flagged @1%':>28}")
res = {}
for name, s in scores.items():
    res[name] = {**mia.metrics(lab, s[:2 * n]), "flag": mia.canaries_flagged(D, s[:2 * n], s[2 * n:]),
                 "canary_auc": mia.canary_auc(D, s[2 * n:])}
    fi, fo = res[name]["flag"]
    print(mia.summary_row(name, res[name], f"  {fi:>12}/{c} in  {fo:>3}/{c} out"))

mu = PH.mean(0)
print()
print(f"{'record':<22} {'member':>6} {'target phi':>10} {'shadow mean':>11} {'LiRA z':>7}")
for j in (0, c):
    i = 2 * n + j
    print(f"{D['can_ids'][j]:<22} {'yes' if j < c else 'no':>6} {pt[i]:10.2f} {mu[i]:11.2f} {lira[i]:7.2f}")
np.savez_compressed(labkit.out("shadows.npz"), phi_shadows=PH, phi_target=pt,
                    pred_in=np.concatenate(P_in), y_in=np.concatenate(Y_in),
                    pred_out=np.concatenate(P_out), y_out=np.concatenate(Y_out))
mia.jdump("shadows.json", {"K": K, "results": res, "canary_ids": D["can_ids"],
                           "canary": {"phi_target": [round(float(v), 3) for v in pt[2 * n:]],
                                      "phi_shadows": [[round(float(v), 3) for v in PH[:, 2 * n + j]] for j in range(2 * c)],
                                      "lira": [round(float(v), 3) for v in lira[2 * n:]]},
                           "lira_threshold": mia.threshold(lira[n:2 * n]), "seconds": round(time.time() - t0, 1)})
L = res["LiRA (offline)"]
print(f"RESULT LiRA flags {L['flag'][0]}/{c} in-canaries ({mia.CANARY}) at 1% FPR, loss threshold "
      f"{res['loss threshold']['flag'][0]}/{c}; average-case AUC {res['loss threshold']['auc']:.3f} -> {L['auc']:.3f}")
