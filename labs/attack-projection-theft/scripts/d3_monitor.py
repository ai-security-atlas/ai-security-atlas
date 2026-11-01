"""Defend D3: watch the queries. Run from labs/:
    docker compose run --rm workbench python attack-projection-theft/scripts/d3_monitor.py

Replays one day of traffic against the full-detail API: the Step-2 thief (random token soup),
an adaptive thief who sends natural sentences instead, and honest users. The operator's monitor
scores sampled logged prompts under the victim itself (mean per-token logprob), flags keys whose
traffic is implausible text, and reports what a per-key budget does to the 700-row floor from
Step 3. The adaptive thief is the honest negative: same queries, ordinary text, spectrum intact.
"""
import json

import labkit

labkit.banner()

import numpy as np  # noqa: E402

import projectionlab as P  # noqa: E402

tok, model = P.load_victim()
pool, honest_prompts = P.load_prompt_pool()
NAT = 700
log = labkit.out("d3_queries.jsonl")
log.unlink(missing_ok=True)

keys = {"app-user": P.Policy(detail="full"),
        "thief": P.Policy(detail="full"),
        "natural-thief": P.Policy(detail="full")}
nat_prompts = P.natural_prompts(pool, NAT)
rand_prompts = P.random_prompts(tok, 600, seed=31)
natural_rows, rand_rows = [], []
with P.Server(tok, model, keys, log_path=log) as api:
    for i in range(0, len(honest_prompts), 20):
        api.post("/v1/score", {"prompts": honest_prompts[i:i + 20], "detail": "full"}, "app-user")
    for i in range(0, 600, P.BATCH):
        _, r = api.post("/v1/score", {"prompts": rand_prompts[i:i + P.BATCH], "detail": "full"}, "thief")
        rand_rows += [P.decode_row(b) for b in r["rows"]]
    for i in range(0, NAT, P.BATCH):
        _, r = api.post("/v1/score", {"prompts": nat_prompts[i:i + P.BATCH], "detail": "full"}, "natural-thief")
        natural_rows += [P.decode_row(b) for b in r["rows"]]

# --- the monitor: score sampled prompts of each key under the victim itself
rows = [r for r in P.read_log(log) if r.get("status") == 200 and r.get("prompts")]
by_key = {}
for r in rows:
    by_key.setdefault(r["key"], []).extend(r["prompts"])
cal = P.score_prompts(model, tok, by_key["app-user"])
threshold = float(np.percentile(cal, 10))
print(f"monitor: mean per-token logprob under the victim, sampled from each key's log")
print(f"honest traffic: median {np.median(cal):.2f}, spread {min(cal):.2f} to {max(cal):.2f} "
      f"(short prompts vary widely)")
print(f"threshold: the honest traffic's 10th percentile {threshold:.2f}; a key is flagged when its")
print(f"median sampled prompt scores below it (individual prompts overlap; keys do not)")
monitor = {}
for key in ("app-user", "thief", "natural-thief"):
    prompts = by_key[key]
    sample = prompts[:48]
    sc = P.score_prompts(model, tok, sample)
    med = float(np.median(sc))
    flagged = med < threshold
    monitor[key] = {"median": round(med, 2), "flagged": bool(flagged),
                    "queries": len(prompts), "sample": len(sample)}
    print(f"  {key:>13}: median {med:7.2f}  queries {len(prompts):5d}  flagged {flagged}")

# --- does the adaptive thief still steal? spectrum of the natural rows
est_nat = P.estimate_dim(np.stack(natural_rows))
B = P.recover_basis(np.stack(natural_rows), model.config.hidden_size)
fit_nat = P.fit_basis(B, model)
print(f"\nnatural-thief's {NAT} ordinary sentences: knee {est_nat['dim']} "
      f"(ratio {est_nat['ratio']:.3g}), basis fit {fit_nat['rel_resid']:.2e} - the theft still works")

# --- and what a budget does to the 700-row floor
budget = 400
keys_b = {"thief": P.Policy(detail="full", budget=budget)}
blog = labkit.out("d3_budget.jsonl")
blog.unlink(missing_ok=True)
refused = None
with P.Server(tok, model, keys_b, log_path=blog, quiet=True) as api:
    got = []
    for i in range(0, NAT, P.BATCH):
        code, r = api.post("/v1/score", {"prompts": nat_prompts[i:i + P.BATCH], "detail": "full"}, "thief")
        if code != 200:
            refused = r
            break
        got += [P.decode_row(b) for b in r["rows"]]
    est_b = P.estimate_dim(np.stack(got))
    print(f"budget {budget}/key: the thief holds {len(got)} rows when HTTP "
          f"{refused['error']} arrives; spectrum knee {est_b['dim']} "
          f"({'clear' if est_b['clear'] else 'no clear knee'}) - short of the ~700-row floor")
P.save("d3.json", {"threshold": round(threshold, 2), "honest_median": round(float(np.median(cal)), 2),
                   "honest_spread": [round(min(cal), 2), round(max(cal), 2)],
                   "monitor": monitor, "natural": {"dim": est_nat["dim"], "ratio": round(est_nat["ratio"], 1),
                                                   "fit": float(f"{fit_nat['rel_resid']:.3g}"), "rows": NAT},
                   "budget": {"cap": budget, "got": len(got), "knee": est_b["dim"],
                              "clear": est_b["clear"]}})
