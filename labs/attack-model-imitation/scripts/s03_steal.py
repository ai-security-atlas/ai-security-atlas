"""Step 3: steal the victim through its API at three detail levels. Run from labs/:
    docker compose run --rm workbench python attack-model-imitation/scripts/s03_steal.py

For each detail level (label, top-3, full probabilities) a separate attacker key sends the 600
unlabelled pool digits to victim-api, then trains a fresh substitute on the first B answers for
each budget B. Fidelity = agreement with the victim's labels on the 297 held-out digits the
attacker never queried. Writes work/steal.json and the 600-query copies
work/copy_<detail>.safetensors (tagged with the lab canary).
"""
import json

import labkit

labkit.banner()

import theft  # noqa: E402
import victim_api  # noqa: E402

BUDGETS = [25, 50, 100, 200, 400, 600]
DETAILS = ["label", "topk", "probs"]

X, y, S = theft.data()
pool, test = X[S["pool"]], X[S["test"]]
victim = theft.load("victim.safetensors")
vtest = theft.predict(victim, test)
keys = {f"thief-{d}": victim_api.KeyPolicy() for d in DETAILS}
log = labkit.out("s03_queries.jsonl")
log.unlink(missing_ok=True)
t = theft.timer()
answers = {}
with theft.victim_server(keys, log=log.name) as url:
    for d in DETAILS:
        res, served, _ = victim_api.VictimClient(url, f"thief-{d}").predict_all(pool, detail=d, k=3)
        answers[d] = res
print(f"queried {len(pool)} pool digits x {len(DETAILS)} detail levels in {t():.1f}s (log: work/{log.name})")
print("fidelity = agreement with the victim on 297 held-out digits")
print(f"{'queries':>8}  " + "  ".join(f"{d:>7}" for d in DETAILS))
fid = {d: {} for d in DETAILS}
for b in BUDGETS:
    for d in DETAILS:
        m = theft.steal(pool[:b], answers[d][:b])
        fid[d][b] = round(theft.agreement(m, test, vtest), 3)
        if b == BUDGETS[-1]:
            theft.save(m, f"copy_{d}.safetensors", canary=theft.CANARY, stolen_via=d, queries=b)
    print(f"{b:>8}  " + "  ".join(f"{fid[d][b]:>7.3f}" for d in DETAILS), flush=True)
first = {d: next((b for b in BUDGETS if fid[d][b] >= 0.95), None) for d in DETAILS}
print("queries to reach 95% agreement: " + ", ".join(f"{d} {first[d] or '>' + str(BUDGETS[-1])}" for d in DETAILS))
print(f"wrote work/copy_label.safetensors work/copy_topk.safetensors work/copy_probs.safetensors (tag {theft.CANARY}) in {t():.0f}s")
labkit.out("steal.json").write_text(json.dumps({"budgets": BUDGETS, "fidelity": fid, "first95": first}))
