"""Step 5: an attacker with no digits at all. Run from labs/:
    docker compose run --rm workbench python attack-model-imitation/scripts/s05_random_queries.py

Same attack as Step 3, but the queries are uniform random 8x8 noise instead of the attacker's
pool of real digits. Shows how the answers are spread over the classes, and the fidelity per
budget for label-only and full-probability answers (Step 3's pool numbers for comparison).
"""
import json

import numpy as np

import labkit

labkit.banner()

import theft  # noqa: E402
import victim_api  # noqa: E402

BUDGETS = [100, 300, 600, 1200]
X, y, S = theft.data()
test = X[S["test"]]
vtest = theft.predict(theft.load("victim.safetensors"), test)
noise = np.random.default_rng(1).uniform(0, 1, (BUDGETS[-1], 64)).astype(np.float32)
keys = {"noise-label": victim_api.KeyPolicy(), "noise-probs": victim_api.KeyPolicy()}
log = labkit.out("s05_queries.jsonl")
log.unlink(missing_ok=True)
with theft.victim_server(keys, log=log.name) as url:
    ans = {d: victim_api.VictimClient(url, f"noise-{d}").predict_all(noise, detail=d)[0] for d in ("label", "probs")}
counts = np.bincount([int(r["label"]) for r in ans["label"]], minlength=10)
print("victim's answers to noise, per class: " + " ".join(f"{c}:{n}" for c, n in enumerate(counts)))
print(f"top-p of the answers: median {np.median([max(r['probs']) for r in ans['probs']]):.2f} (held-out digits: "
      f"{np.median(theft.proba_fn(theft.load('victim.safetensors'))(test).max(1)):.2f})")
steal = json.loads(labkit.inp("work/steal.json").read_text()) if labkit.inp("work/steal.json").exists() else None
print(f"{'queries':>8}  {'label':>7}  {'probs':>7}")
fid = {"label": {}, "probs": {}}
for b in BUDGETS:
    for d in fid:
        fid[d][b] = round(theft.agreement(theft.steal(noise[:b], ans[d][:b]), test, vtest), 3)
    print(f"{b:>8}  {fid['label'][b]:>7.3f}  {fid['probs'][b]:>7.3f}", flush=True)
if steal:
    print(f"with 600 real digits (Step 3): label {steal['fidelity']['label']['600']:.3f}  probs {steal['fidelity']['probs']['600']:.3f}")
labkit.out("noise.json").write_text(json.dumps({"budgets": BUDGETS, "fidelity": fid, "class_counts": counts.tolist()}))
