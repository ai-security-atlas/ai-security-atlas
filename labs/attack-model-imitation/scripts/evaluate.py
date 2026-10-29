"""Evaluate: re-measure the attack and each defense in one run. Run from labs/:
    docker compose run --rm workbench python attack-model-imitation/scripts/evaluate.py

Needs only work/victim.safetensors (Step 1). One victim-api server, one key per condition:
  probs / label           Step 3: fidelity at 50, 100 and 600 queries
  round-2                 D1: probabilities rounded to 2 decimals
  budget-100 (1 key)      D2: label-only, 100 queries per key; and 6 such keys
  watermark               D3: hits of each copy on its own key's watermark set, independent model as control
  fingerprint             D3: agreement with the victim on 100 blended digits
Prints the table, then compares the shape (not exact numbers) with expected/evaluate.json and
ends with "RESULT: REPRODUCED" or "RESULT: MISMATCH (...)".
"""
import json

import numpy as np

import labkit

labkit.banner()

import theft  # noqa: E402
import victim_api  # noqa: E402

X, y, S = theft.data()
pool, test = X[S["pool"]], X[S["test"]]
victim = theft.load("victim.safetensors")
vtest = theft.predict(victim, test)
P = victim_api.KeyPolicy
keys = {"probs": P(), "label": P(max_detail="label"), "round-2": P(round_digits=2),
        **{f"budget-{i}": P(budget=100, max_detail="label") for i in range(6)}}
log = labkit.out("eval_queries.jsonl")
log.unlink(missing_ok=True)
log.with_suffix(".wm.jsonl").unlink(missing_ok=True)


def fid(Xq, res):
    return round(theft.agreement(theft.steal(Xq, res), test, vtest), 3)


A = {}
with theft.victim_server(keys, log=log.name, quiet=True) as url:
    for k in ("probs", "label", "round-2"):
        A[k] = victim_api.VictimClient(url, k).predict_all(pool, detail="probs")[0]
    one = victim_api.VictimClient(url, "budget-0").predict_all(pool, detail="probs")[0]
    many = one + [r for i in range(1, 6) for r in
                  victim_api.VictimClient(url, f"budget-{i}").predict_all(pool[i * 100:(i + 1) * 100], detail="probs")[0]]
wm_keys = {"wm-label": P(max_detail="label"), "wm-probs": P()}
wlog = labkit.out("eval_wm_queries.jsonl")
wlog.unlink(missing_ok=True)
wlog.with_suffix(".wm.jsonl").unlink(missing_ok=True)
copies = {}
with theft.victim_server(wm_keys, log=wlog.name, watermark=victim_api.Watermark(theft.CANARY, 0.02), quiet=True) as url:
    for k in wm_keys:
        copies[k] = theft.steal(pool, victim_api.VictimClient(url, k).predict_all(pool, detail="probs")[0])
marks = victim_api.read_log(wlog.with_suffix(".wm.jsonl"))
indep = theft.fit(theft.mlp(3), pool, y[S["pool"]])


def hits(m, k):
    Xw = np.array([r["input"] for r in marks if r["key"] == k], np.float32)
    lw = np.array([int(r["label"]) for r in marks if r["key"] == k])
    return float((theft.predict(m, Xw) == lw).mean())


ref = theft.fit(theft.mlp(11), X[S["victim"]], y[S["victim"]])
g = np.random.default_rng(5)
a, b = g.choice(S["victim"], 3000), g.choice(S["victim"], 3000)
blend = (0.5 * X[a[y[a] != y[b]]] + 0.5 * X[b[y[a] != y[b]]]).astype(np.float32)
vb, rb = theft.predict(victim, blend), theft.predict(ref, blend)
fp, fv = blend[vb != rb][:100], vb[vb != rb][:100]
fprint = {k: float((theft.predict(m, fp) == fv).mean()) for k, m in {**copies, "independent": indep}.items()}

m = {
    "probs@50": fid(pool[:50], A["probs"][:50]), "label@50": fid(pool[:50], A["label"][:50]),
    "probs@100": fid(pool[:100], A["probs"][:100]), "label@200": fid(pool[:200], A["label"][:200]),
    "round-2@50": fid(pool[:50], A["round-2"][:50]), "probs@600": fid(pool, A["probs"]),
    "budget: 1 key": fid(pool[:len(one)], one), "budget: 6 keys": fid(pool[:len(many)], many),
}
w = {"label copy": hits(copies["wm-label"], "wm-label"), "probs copy": hits(copies["wm-probs"], "wm-probs"),
     "independent": max(hits(indep, "wm-label"), hits(indep, "wm-probs"))}
print(f"{'measurement':<34} value")
for k, v in m.items():
    print(f"{'fidelity ' + k:<34} {v:.3f}")
print(f"{'queries served to 1 budget key':<34} {len(one)}")
for k, v in w.items():
    print(f"{'watermark hits, ' + k:<34} {v:.2f}")
for k, v in fprint.items():
    print(f"{'fingerprint, ' + k.replace('wm-', '') + (' copy' if k != 'independent' else ''):<34} {v:.2f}")

got = {
    "probs beat labels at 50 queries": m["probs@50"] >= m["label@50"] + 0.05,
    "probs reach 95% by 100 queries": m["probs@100"] >= 0.95,
    "labels below 95% at 200 queries": m["label@200"] < 0.95,
    "rounding to 2 decimals slows the thief": m["round-2@50"] <= m["probs@50"] - 0.05,
    "budget stops one key at 100": len(one) == 100,
    "six keys beat the budget": m["budget: 6 keys"] >= m["budget: 1 key"] + 0.05,
    "watermark catches the label copy": w["label copy"] >= 0.8 and w["independent"] <= 0.2,
    "watermark misses the probs copy": w["probs copy"] <= 0.2,
    "fingerprint flags the probs copy": fprint["wm-probs"] >= fprint["independent"] + 0.15,
}
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
for k, v in got.items():
    print(f"[{'ok' if v == expected.get(k) else '!!'}] {k}: {v}")
labkit.out("evaluate.json").write_text(json.dumps({"measured": m, "watermark": w, "fingerprint": fprint, "checks": got}))
diff = [k for k in expected if got.get(k) != expected[k]]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
