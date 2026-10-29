"""Step D3: prove a suspect model was copied (watermark and fingerprint). Run from labs/:
    docker compose run --rm workbench python attack-model-imitation/scripts/d3_watermark_check.py

Watermark (DAWN-style): the server answers a keyed-hash-selected 2% of inputs with a wrong
label and records them per API key in work/d3_queries.wm.jsonl. The secret is the lab canary.
Two thieves each send the 600 pool digits: one key is label-only, one gets full probabilities.
Each trains a copy. The owner then asks three suspects (the two copies and an independent model
trained on true labels without the API) to label the recorded inputs: a copy repeats the wrong
answers, an independent model should not. p = chance of that many hits if each hit had
probability 1/10.
Fingerprint (no server change): 100 blended digits (half one digit, half another) on which the
victim and the owner's own second model disagree. A copy follows the victim there more often.
"""
import json

import numpy as np
from scipy.stats import binom

import labkit

labkit.banner()

import theft  # noqa: E402
import victim_api  # noqa: E402

X, y, S = theft.data()
pool = X[S["pool"]]
victim = theft.load("victim.safetensors")
keys = {"thief-label": victim_api.KeyPolicy(max_detail="label"), "thief-probs": victim_api.KeyPolicy()}
log = labkit.out("d3_queries.jsonl")
log.unlink(missing_ok=True)
log.with_suffix(".wm.jsonl").unlink(missing_ok=True)
wm = victim_api.Watermark(secret=theft.CANARY, rate=0.02)
copies = {}
with theft.victim_server(keys, log=log.name, watermark=wm) as url:
    for k in keys:
        res = victim_api.VictimClient(url, k).predict_all(pool, detail="probs")[0]
        copies[f"copy ({k[6:]})"] = theft.steal(pool, res)
marks = victim_api.read_log(log.with_suffix(".wm.jsonl"))
print(f"watermark: secret {theft.CANARY}, rate 2% -> {len(marks)} of {2 * len(pool)} answers were deliberately wrong")
suspects = {**copies, "independent": theft.fit(theft.mlp(3), pool, y[S["pool"]])}
wm_sets = {k: (np.array([m["input"] for m in marks if m["key"] == k], np.float32),
               np.array([int(m["label"]) for m in marks if m["key"] == k])) for k in keys}

ref = theft.fit(theft.mlp(11), X[S["victim"]], y[S["victim"]])      # the owner's own second model
g = np.random.default_rng(5)
a, b = g.choice(S["victim"], 3000), g.choice(S["victim"], 3000)
keep = y[a] != y[b]
blend = (0.5 * X[a[keep]] + 0.5 * X[b[keep]]).astype(np.float32)
vb, rb = theft.predict(victim, blend), theft.predict(ref, blend)
fp, fv = blend[vb != rb][:100], vb[vb != rb][:100]

print(f"{'suspect':<14} {'wm set':<12} {'hits':>6} {'p':>8}  {'fingerprint':>11}")
out = {}
for name, m in suspects.items():
    for k, (Xw, lw) in wm_sets.items():
        if name.startswith("copy") and k[6:] not in name:
            continue
        h = int((theft.predict(m, Xw) == lw).sum())
        p = float(binom.sf(h - 1, len(lw), 0.1))
        f = float((theft.predict(m, fp) == fv).mean())
        out[f"{name} | {k}"] = {"hits": h, "n": len(lw), "p": p, "fingerprint": round(f, 2)}
        print(f"{name:<14} {k:<12} {h:>3}/{len(lw):<2} {p:>8.0e}  {f:>11.2f}")
lab_acc = float((theft.predict(suspects["copy (label)"], X[S["test"]]) == y[S["test"]]).mean())
print(f"cost: every caller, honest or not, got a deliberately wrong label on {len(marks) / (2 * len(pool)):.1%} of answers; the label copy scores {lab_acc:.3f} on the test digits")
labkit.out("d3.json").write_text(json.dumps({"n_marks": len(marks), "checks": out}))
