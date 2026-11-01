"""Step 2: the attacker collects full logit rows. Run from labs/:
    docker compose run --rm workbench python attack-projection-theft/scripts/s02_collect.py

Sends 1,200 random-token prompts to lantern-mini-1 in 12 batched requests and stacks the
answered rows into work/rows.npy. This is the whole attack surface: ordinary API calls, counted
and logged like any traffic.
"""
import time

import labkit

labkit.banner()

import numpy as np  # noqa: E402

import projectionlab as P  # noqa: E402

tok, model = P.load_victim()
keys = {"attacker": P.Policy(detail="full")}
log = labkit.out("s02_queries.jsonl")
log.unlink(missing_ok=True)
prompts = P.random_prompts(tok, P.N_ROWS)
print(f"attacker's prompts: {P.N_ROWS} strings of random decoded tokens (seed {P.PROMPT_SEED})")
print(f"example: {prompts[0][:60]!r}")
rows = []
t0 = time.time()
with P.Server(tok, model, keys, log_path=log) as api:
    for i in range(0, P.N_ROWS, P.BATCH):
        code, r = api.post("/v1/score", {"prompts": prompts[i:i + P.BATCH], "detail": "full"}, "attacker")
        assert code == 200, r
        rows += [P.decode_row(b) for b in r["rows"]]
    secs = time.time() - t0
    M = np.stack(rows)
    q = api.queries
print(f"collected {M.shape[0]} rows x {M.shape[1]:,} logprobs in {secs:.1f}s "
      f"({q} HTTP requests, {P.N_ROWS} prompts answered)")
print(f"row 0: min {M[0].min():.2f}  max {M[0].max():.4f}  mean {M[0].mean():.2f}")
np.save(labkit.out("rows.npy"), M)
P.save("s02.json", {"rows": int(M.shape[0]), "vocab": int(M.shape[1]), "requests": q,
                    "prompts": P.N_ROWS, "seconds": round(secs, 1), "seed": P.PROMPT_SEED})
print(f"wrote work/rows.npy ({M.nbytes / 1e6:.0f} MB, float32) - the attacker's only dataset")
