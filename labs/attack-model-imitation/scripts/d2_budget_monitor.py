"""Step D2: per-key query budgets and a look at the query log. Run from labs/:
    docker compose run --rm workbench python attack-model-imitation/scripts/d2_budget_monitor.py

The server keeps D1's label-only answers and adds a budget of 100 queries per key. Four
callers: one thief with one key, the same thief with six keys (sybil accounts), an honest app
user sending 60 held-out digits, and a noise prober sending 100 random images. Then a simple
monitor reads work/d2_queries.jsonl: per key, the queries served and refused and the share of
low-confidence answers (top probability < 0.9), which in-distribution digits rarely produce.
"""
import json
from collections import defaultdict

import numpy as np

import labkit

labkit.banner()

import theft  # noqa: E402
import victim_api  # noqa: E402

BUDGET, SYBILS = 100, 6
X, y, S = theft.data()
pool, test = X[S["pool"]], X[S["test"]]
vtest = theft.predict(theft.load("victim.safetensors"), test)
noise = np.random.default_rng(1).uniform(0, 1, (100, 64)).astype(np.float32)
pol = victim_api.KeyPolicy(budget=BUDGET, max_detail="label")
names = ["thief"] + [f"sybil-{i}" for i in range(1, SYBILS + 1)] + ["app-user", "noise-probe"]
keys = {k: pol for k in names}
log = labkit.out("d2_queries.jsonl")
log.unlink(missing_ok=True)
with theft.victim_server(keys, log=log.name) as url:
    one, _, err = victim_api.VictimClient(url, "thief").predict_all(pool, detail="probs")
    print(f"thief, 1 key: {len(one)} answers, then HTTP 429 ({err.usage})")
    many = []
    for i in range(SYBILS):
        part = pool[i * BUDGET:(i + 1) * BUDGET]
        many += victim_api.VictimClient(url, f"sybil-{i + 1}").predict_all(part, detail="probs")[0]
    print(f"thief, {SYBILS} keys x {BUDGET}: {len(many)} answers, no 429")
    victim_api.VictimClient(url, "app-user").predict_all(test[:60], detail="label")
    victim_api.VictimClient(url, "noise-probe").predict_all(noise, detail="label")
f1 = theft.agreement(theft.steal(pool[:len(one)], one), test, vtest)
fn = theft.agreement(theft.steal(pool[:len(many)], many), test, vtest)
print(f"fidelity: 1 key {f1:.3f} · {SYBILS} keys {fn:.3f}")

stats = defaultdict(lambda: {"served": 0, "refused": 0, "top_p": []})
for row in victim_api.read_log(log):
    s = stats[row["key"]]
    if row["status"] == 200:
        s["served"] += row["n"]
        s["top_p"] += row["top_p"]
    else:
        s["refused"] += row["n"]
print(f"monitor over work/{log.name}:")
print(f"{'key':<12} {'served':>6} {'refused':>7} {'low-conf':>8}  flags")
report = {}
for k in names:
    s = stats[k]
    low = float(np.mean(np.array(s["top_p"]) < 0.9)) if s["top_p"] else 0.0
    flags = [f for f, on in (("at budget", s["served"] >= BUDGET), ("refused", s["refused"] > 0),
                             ("low-confidence", low > 0.2)) if on]
    report[k] = {"served": s["served"], "refused": s["refused"], "low_conf": round(low, 2), "flags": flags}
    print(f"{k:<12} {s['served']:>6} {s['refused']:>7} {low:>8.2f}  {', '.join(flags) or '-'}")
labkit.out("d2.json").write_text(json.dumps({"budget": BUDGET, "sybils": SYBILS, "fid_one": round(f1, 3),
                                             "fid_sybil": round(fn, 3), "monitor": report}))
