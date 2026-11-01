"""Defend D1: serve less - top-k only, and the logit_bias escape. Run from labs/:
    docker compose run --rm workbench python attack-projection-theft/scripts/d1_serve_less.py

Two hardened policies against the same attack. (a) top-5 answers with no logit_bias: full rows
are refused, and 400 top-5 answers leave 2,000 (token, value) pairs whose positions never
complete a row, so there is no matrix to factor. (b) top-5 with logit_bias still accepted: the
attacker biases 4 tokens into view per request and reads exact logit differences - measured here
on a 256-token block, then extrapolated to the whole attack cost. Ends with what honest users
keep and lose under each policy.
"""
import math

import labkit

labkit.banner()

import numpy as np  # noqa: E402
import torch  # noqa: E402

import projectionlab as P  # noqa: E402

tok, model = P.load_victim()
V = len(tok)
N_TOPK = 400
BLOCK = list(range(1200, 1456))
log = labkit.out("d1_queries.jsonl")
log.unlink(missing_ok=True)

print("policy (a): top-5 answers, logit_bias refused")
keys_a = {"thief": P.Policy(detail="topk", top_k=5, allow_logit_bias=False)}
with P.Server(tok, model, keys_a, log_path=log.with_suffix(".a.jsonl"), quiet=True) as api:
    code, r = api.post("/v1/score", {"prompts": ["The vault door opens with"], "detail": "full"}, "thief")
    print(f"  full-row request -> HTTP {code} {r['error']}")
    code, r = api.post("/v1/score", {"prompts": ["The vault door opens with"], "detail": "topk",
                                     "logit_bias": {"1200": P.BIAS}}, "thief")
    print(f"  logit_bias request -> HTTP {code} {r['error']}")
    seen = set()
    rows_topk = []
    prompts = P.random_prompts(tok, N_TOPK, seed=17)
    for i in range(0, N_TOPK, P.BATCH):
        code, r = api.post("/v1/score", {"prompts": prompts[i:i + P.BATCH], "detail": "topk"}, "thief")
        for row in r["rows"]:
            seen.update(e["id"] for e in row["top"])
            rows_topk.append(row["top"])
    q_a = api.queries
    print(f"  {N_TOPK} top-5 answers -> {len(seen):,} distinct token ids seen once or twice; "
          f"no row is ever complete (a full row needs all {V:,})")
    print(f"  example answer: {[(e['token'], round(e['logprob'], 3)) for e in rows_topk[0][:3]]}")

print("\npolicy (b): top-5 answers, logit_bias still accepted (the escape)")
keys_b = {"thief": P.Policy(detail="topk", top_k=5, allow_logit_bias=True)}
prompt = "The vault door opens with"
enc = tok(prompt, return_tensors="pt").input_ids
with torch.no_grad():
    logits = model(enc).logits[0, -1].float()
errs, queries = [], 0
with P.Server(tok, model, keys_b, log_path=log.with_suffix(".b.jsonl"), quiet=True) as api:
    for i in range(0, len(BLOCK), 4):
        four = BLOCK[i:i + 4]
        code, r = api.post("/v1/score", {"prompts": [prompt], "detail": "topk",
                                         "logit_bias": {str(t): P.BIAS for t in four}}, "thief")
        top = {e["id"]: e["logprob"] for e in r["rows"][0]["top"]}
        missing = [t for t in four if t not in top]
        assert not missing, f"bias {P.BIAS} did not lift {missing} into the top-5"
        ref = next(t for t in top if t not in four)   # the best unbiased token rides along at rank 5
        g = top[ref]
        for t in four:
            rec = (top[t] - g) - P.BIAS
            errs.append(abs(rec - float(logits[t] - logits[ref])))
    queries = api.queries
    print(f"  biased {len(BLOCK)} hidden tokens into view in {queries} requests "
          f"(4 exact logit differences per request)")
    print(f"  max error vs the true logits: {max(errs):.1e} (the softmax normalizer cancels)")
    per_row = math.ceil(V / 4)
    rows_needed = 577
    total = rows_needed * per_row
    print(f"  full attack: {rows_needed} rows x {per_row:,} requests = {total:,} requests "
          f"vs the {P.N_ROWS:,} of the full-row attack ({total / P.N_ROWS:,.0f}x)")

print("\nwhat each side keeps:")
print("  honest users: top-5 logprobs still cover ranking, classification and sampling controls")
print("  the API loses: whole-distribution scoring (a real feature, e.g. evaluation harnesses)")
print("  verdict: top-k alone is not enough while logit_bias exists; both switches must be off")
P.save("d1.json", {"refused_full": 403, "refused_bias": 400, "topk_rows": N_TOPK,
                   "distinct_ids": len(seen), "queries_a": q_a, "block": len(BLOCK),
                   "block_queries": queries, "per_request": 4, "max_err": float(max(errs)),
                   "per_row_requests": per_row, "rows_needed": rows_needed, "total_requests": total,
                   "factor": round(total / P.N_ROWS)})
