"""Step D2: serve labels only, through victim-api. Run from labs/:
    docker compose run --rm workbench python attack-membership/scripts/d2_label_only.py
Puts the target behind the shared victim-api fixture (127.0.0.1 inside this container) with two keys:
"partner" may read probabilities, "public" is capped at the label. The attacker asks the public key
for probabilities and gets labels. It then tries two label-only attacks: the gap attack, and an
augmentation attack (Choquette-Choo et al. 2021) that sends 30 noisy copies of each record (Gaussian,
sigma 0.2, seeded) and counts how often the label survives. Writes WORK/label_only.json and the query log.
"""
import numpy as np
import torch

import labkit

labkit.banner()

import mia  # noqa: E402
import victim_api  # noqa: E402

D = mia.data()
n, c, lab = D["n"], D["c"], D["is_member"]
ax_, ay_ = mia.audit_x(D)
model = mia.target()
R, SIGMA = 30, 0.2


def predict_proba(X):
    return mia.logprobs(model, torch.tensor(X, dtype=torch.float32).reshape(-1, 1, 8, 8)).exp().numpy()


log = labkit.out("queries.jsonl")
log.unlink(missing_ok=True)
app = victim_api.create_app(predict_proba, classes=[str(i) for i in range(10)], n_features=64, model_id=mia.TARGET,
                            keys={"partner": victim_api.KeyPolicy(), "public": victim_api.KeyPolicy(max_detail="label")},
                            log_path=log, log_inputs=False)
flat = ax_.reshape(len(ax_), 64).numpy()
yy = ay_.numpy()
rows = {}
with victim_api.serve(app) as url:
    partner, public = victim_api.VictimClient(url, "partner"), victim_api.VictimClient(url, "public")
    one = public.predict(flat[:1], detail="probs")
    print(f"public key asks detail=probs -> served {one['detail']!r}: {one['results'][0]}")
    res, served, _ = partner.predict_all(flat, detail="probs", batch=420)
    P = np.array([r["probs"] for r in res])
    rows["loss (partner: probs)"] = (np.log(P[np.arange(len(yy)), yy] + 1e-300), len(flat))
    res, served, _ = public.predict_all(flat, detail="probs", batch=420)
    rows["gap (public: label)"] = ((np.array([int(r["label"]) for r in res]) == yy).astype(float), len(flat))
    rng = np.random.default_rng(0)
    hits = np.zeros(len(flat))
    for _ in range(R):
        noisy = np.clip(flat + rng.normal(0, SIGMA, flat.shape), 0, 1)
        res, _, _ = public.predict_all(noisy, detail="label", batch=420)
        hits += np.array([int(r["label"]) for r in res]) == yy
    rows[f"augmented x{R} (public)"] = (hits / R, R * len(flat))
    usage = public.usage()

print(mia.HEADER + f"  {'canaries in/out @1%':>20} {'canary AUC':>10} {'queries':>8}")
out = {}
for name, (s, q) in rows.items():
    m = {**mia.metrics(lab, s[:2 * n]), "flag": mia.canaries_flagged(D, s[:2 * n], s[2 * n:]),
         "canary_auc": mia.canary_auc(D, s[2 * n:]), "queries": q}
    out[name] = m
    print(mia.summary_row(name[:22], m, f"  {m['flag'][0]:>7}/{c} in {m['flag'][1]:>2}/{c} out {m['canary_auc']:10.2f} {q:>8}"))
served = sorted({r['served'] for r in victim_api.read_log(log) if r['key'] == 'public'})
print(f"query log: {len(victim_api.read_log(log))} requests; public key used {usage['used']} rows, served detail {served}")
mia.jdump("label_only.json", {"R": R, "sigma": SIGMA, "rows": out})
a, g = out[f"augmented x{R} (public)"], out["gap (public: label)"]
print(f"RESULT label-only: gap AUC {g['auc']:.3f}, augmented AUC {a['auc']:.3f} with {a['queries']} queries; "
      f"TPR at 1% FPR {mia.pct(a['tpr1']).strip()}, canary AUC {a['canary_auc']:.2f}")
