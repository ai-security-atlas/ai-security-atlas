"""Step D1: answer with less (label only, rounding) and measure the thief again. Run from labs/:
    docker compose run --rm workbench python attack-model-imitation/scripts/d1_output_minimization.py

Five server policies, one attacker key each. The attacker always asks for detail=probs with
k=1; the key's policy decides what is served. Fidelity per budget on the 297 held-out digits,
as in Step 3. The label column is what an honest user still gets: unchanged in every policy.
"""
import json

import labkit

labkit.banner()

import theft  # noqa: E402
import victim_api  # noqa: E402

BUDGETS = [50, 100, 200, 600]
POLICIES = {
    "probs (full)": victim_api.KeyPolicy(),
    "probs round 2": victim_api.KeyPolicy(round_digits=2),
    "probs round 1": victim_api.KeyPolicy(round_digits=1),
    "top-1 + p": victim_api.KeyPolicy(max_detail="topk", round_digits=2),
    "label only": victim_api.KeyPolicy(max_detail="label"),
}
X, y, S = theft.data()
pool, test = X[S["pool"]], X[S["test"]]
vtest = theft.predict(theft.load("victim.safetensors"), test)
keys = {f"k{i}": p for i, p in enumerate(POLICIES.values())}
log = labkit.out("d1_queries.jsonl")
log.unlink(missing_ok=True)
ans, served = {}, {}
with theft.victim_server(keys, log=log.name) as url:
    for i, name in enumerate(POLICIES):
        ans[name], served[name], _ = victim_api.VictimClient(url, f"k{i}").predict_all(pool, detail="probs", k=1)
same = all([r["label"] for r in ans[n]] == [r["label"] for r in ans["probs (full)"]] for n in POLICIES)
print(f"attacker asks for probs; every policy serves the same labels: {same}")
print(f"{'policy':<14} {'served':<7} " + " ".join(f"{b:>6}" for b in BUDGETS) + "   (queries -> fidelity)")
fid = {}
for name in POLICIES:
    fid[name] = {b: round(theft.agreement(theft.steal(pool[:b], ans[name][:b]), test, vtest), 3) for b in BUDGETS}
    print(f"{name:<14} {served[name]:<7} " + " ".join(f"{fid[name][b]:>6.3f}" for b in BUDGETS), flush=True)
labkit.out("d1.json").write_text(json.dumps({"budgets": BUDGETS, "fidelity": fid, "served": served}))
