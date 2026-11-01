"""Step 1: meet the victim API. Run from labs/:
    docker compose run --rm workbench python attack-projection-theft/scripts/s01_meet_api.py

Downloads the pinned 135M victim (first run only), serves it as lantern-mini-1 on 127.0.0.1
inside the container, and shows everything a caller can see: the model card (no architecture),
one greedy completion, and one full logprob row. The operator-side truth (hidden size, tied
projection) is printed only at the end, clearly marked - the attacker never sees it.
"""
import json

import labkit

labkit.banner()

import numpy as np  # noqa: E402

import projectionlab as P  # noqa: E402
import tinylm  # noqa: E402

tok, model = P.load_victim(download=True)
true_d = model.config.hidden_size
true_v = len(tok)
n_params = sum(p.numel() for p in model.parameters())
head_params = model.lm_head.weight.numel()

keys = {"guest": P.Policy(detail="full")}
log = labkit.out("s01_queries.jsonl")
log.unlink(missing_ok=True)
print(f"[note] victim card, as a caller sees it:")
with P.Server(tok, model, keys, log_path=log) as api:
    code, card = api.get("/v1/model")
    print(json.dumps(card, indent=1)[:400])
    pool, honest = P.load_prompt_pool()
    prompt = honest[0]
    prompts = [prompt]
    code, r = api.post("/v1/score", {"prompts": prompts, "detail": "full"}, "guest")
    row = P.decode_row(r["rows"][0])
    top = np.argsort(-row)[:5]
    print(f"\none scored prompt: {prompt!r}")
    print(f"answer: one row of {len(row):,} logprobs (the whole next-token distribution)")
    for i in top:
        print(f"  {tok.decode([int(i)]):>12}  logprob {row[i]:+.4f}")
    code, r2 = api.post("/v1/score", {"prompts": [honest[1]], "detail": "topk"}, "guest")
    print(f"topk answer for {honest[1]!r}:")
    for e in r2["rows"][0]["top"][:3]:
        print(f"  {e['token']!r:>14}  logprob {e['logprob']:+.4f}")
    print(f"usage after {api.queries} requests: {r2['usage']}")

print(f"\n[operator] the card hides it, but this victim is {tinylm.MODELS['smollm2-135m'][0]}:")
print(f"[operator] hidden size {true_d}, vocabulary {true_v:,}, {n_params:,} parameters, "
      f"tie_word_embeddings={model.config.tie_word_embeddings}")
print(f"[operator] the output projection (lm_head) is {head_params:,} parameters "
      f"({100 * head_params / n_params:.1f}% of the model) and is tied to the input embedding table")
P.save("s01.json", {"prompt": prompt, "vocab": true_v, "hidden": true_d, "params": n_params,
                    "head_params": head_params, "queries": api.queries,
                    "top5": [[tok.decode([int(i)]), float(row[i])] for i in top],
                    "canary": P.CANARY})
