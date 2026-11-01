"""Evaluate: re-measure the attack and each defense in one run. Run from labs/:
    docker compose run --rm workbench python attack-projection-theft/scripts/evaluate.py

Uses the rows you collected in Step 2 (it re-collects a small stack if work/rows.npy is gone)
and the defense outputs in work/. Recomputes the headline numbers, checks the canary tag on the
stolen artifact, compares the shape (not exact numbers) with expected/evaluate.json and ends
with "RESULT: REPRODUCED" or "RESULT: MISMATCH (...)".
"""
import json

import labkit

labkit.banner()

import numpy as np  # noqa: E402
from safetensors import safe_open  # noqa: E402

import projectionlab as P  # noqa: E402

tok, model = P.load_victim()
d = model.config.hidden_size

rows_path = labkit.inp("work/rows.npy")
if rows_path.exists():
    M = np.load(rows_path)
else:
    keys = {"attacker": P.Policy(detail="full")}
    log = labkit.out("eval_queries.jsonl")
    log.unlink(missing_ok=True)
    prompts = P.random_prompts(tok, 700)
    with P.Server(tok, model, keys, log_path=log, quiet=True) as api:
        rows = []
        for i in range(0, 700, P.BATCH):
            _, r = api.post("/v1/score", {"prompts": prompts[i:i + P.BATCH], "detail": "full"}, "attacker")
            rows += [P.decode_row(b) for b in r["rows"]]
        M = np.stack(rows)

est = P.estimate_dim(M)
B = P.recover_basis(M, d)
fit = P.fit_basis(B, model)
s = P.singular_values(M)
_, ratio = P.knee(s)
print(f"{'measurement':<44} value")
print(f"{'hidden size estimated (true ' + str(d) + ')':<44} {est['dim']}")
print(f"{'spectrum knee ratio s[k-1]/s[k]':<44} {ratio:.3g}")
print(f"{'projection fit residual (operator-side)':<44} {fit['rel_resid']:.2e}")
print(f"{'principal-angle cosine, worst direction':<44} {fit['cos_min']:.6f}")

d1 = json.loads(labkit.inp("work/d1.json").read_text())
d2 = json.loads(labkit.inp("work/d2.json").read_text())
d3 = json.loads(labkit.inp("work/d3.json").read_text())
print(f"{'D1 full rows under top-k policy':<44} HTTP {d1['refused_full']}")
print(f"{'D1 logits per biased request':<44} {d1['per_request']}")
print(f"{'D1 extrapolated attack cost (requests)':<44} {d1['total_requests']:,} ({d1['factor']:,}x)")
print(f"{'D2 levels that still leak the size':<44} "
      f"{', '.join(k for k, v in d2['levels'].items() if v['clear']) or 'none'}")
print(f"{'D2 round=1 ties in top-5 answers':<44} {d2['ties']['1']}/200")
print(f"{'D3 random-prompt thief flagged':<44} {d3['monitor']['thief']['flagged']}")
print(f"{'D3 natural-text thief flagged':<44} {d3['monitor']['natural-thief']['flagged']}")
print(f"{'D3 natural-text theft still works (knee)':<44} {d3['natural']['dim']}")
print(f"{'D3 budget key stopped at rows':<44} {d3['budget']['got']} (knee {d3['budget']['knee']})")

art = labkit.inp("work/recovered_projection.safetensors")
tag = None
if art.exists():
    with safe_open(str(art), framework="pt") as f:
        tag = f.metadata()["canary"]
print(f"{'stolen artifact carries the canary':<44} {tag}")

got = {
    "hidden size read off the logits": est["dim"] == d,
    "knee ratio is clear (>= 10x)": est["clear"],
    "projection fits inside the recovered span": fit["rel_resid"] < 1e-3,
    "principal angles are zero to 4 decimals": round(fit["cos_min"], 4) == 1.0,
    "D1 top-k policy refuses full rows": d1["refused_full"] == 403,
    "D1 top-k policy refuses logit_bias": d1["refused_bias"] == 400,
    "D1 biased requests leak 4 exact logits": d1["per_request"] == 4 and d1["max_err"] < 1e-4,
    "D1 escape costs >1000x the full-row attack": d1["factor"] > 1000,
    "D2 round=1 kills the size read": not d2["levels"]["round=1"]["clear"],
    "D2 noise=1e-1 kills the size read": not d2["levels"]["noise=1e-1"]["clear"],
    "D2 round=2 still leaks the size weakly": d2["levels"]["round=2"]["dim"] == d,
    "D2 round=2 degrades the basis fit": d2["levels"]["round=2"]["fit"] > 1e-3,
    "D3 flags the random-prompt thief": d3["monitor"]["thief"]["flagged"],
    "D3 does not flag honest users": not d3["monitor"]["app-user"]["flagged"],
    "D3 misses the natural-text thief": not d3["monitor"]["natural-thief"]["flagged"],
    "D3 natural-text theft still recovers the size": d3["natural"]["dim"] == d,
    "D3 budget caps one key below the row floor": d3["budget"]["got"] <= d3["budget"]["cap"],
    "stolen artifact is tagged with the canary": tag == P.CANARY,
}
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
for k, v in got.items():
    print(f"[{'ok' if v == expected.get(k) else '!!'}] {k}: {v}")
labkit.out("evaluate.json").write_text(json.dumps({
    "dim": est["dim"], "ratio": float(f"{ratio:.3g}"), "fit": fit, "d1": d1, "d2": d2, "d3": d3,
    "canary_tag": tag, "checks": got}, indent=1) + "\n", encoding="utf-8")
diff = [k for k in got if got[k] != expected.get(k)] + [k for k in expected if k not in got]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
