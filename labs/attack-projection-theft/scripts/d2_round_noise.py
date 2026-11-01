"""Defend D2: round the logprobs and add noise. Run from labs/:
    docker compose run --rm workbench python attack-projection-theft/scripts/d2_round_noise.py

Replays the same collection (600 fresh rows per condition) against policies that degrade the
numbers before they leave the server, and remeasures the spectrum and the recovered-basis fit
at every level. Also measures the honest cost: ties that rounding creates inside top-5 answers.
"""
import labkit

labkit.banner()

import numpy as np  # noqa: E402

import projectionlab as P  # noqa: E402

tok, model = P.load_victim()
d = model.config.hidden_size
N = 600
LEVELS = [("round=2", dict(round_digits=2)), ("round=1", dict(round_digits=1)), ("round=0", dict(round_digits=0)),
          ("noise=1e-3", dict(noise=1e-3)), ("noise=1e-2", dict(noise=1e-2)), ("noise=1e-1", dict(noise=1e-1))]
prompts = P.random_prompts(tok, N, seed=23)
log = labkit.out("d2_queries.jsonl")
log.unlink(missing_ok=True)

print(f"policy                  knee  ratio s[k-1]/s[k]   clear   basis fit vs true")
table = {}
for name, kw in LEVELS:
    keys = {"thief": P.Policy(detail="full", **kw)}
    with P.Server(tok, model, keys, log_path=log, quiet=True) as api:
        rows = []
        for i in range(0, N, P.BATCH):
            code, r = api.post("/v1/score", {"prompts": prompts[i:i + P.BATCH], "detail": "full"}, "thief")
            assert code == 200, r
            rows += [P.decode_row(b) for b in r["rows"]]
        M = np.stack(rows)
    est = P.estimate_dim(M)
    B = P.recover_basis(M, d)
    fit = P.fit_basis(B, model)["rel_resid"]
    clear = "yes" if est["clear"] else "no"
    print(f"{name:>18}  {est['dim']:>6}  {est['ratio']:>15.3g}   {clear:>3}   {fit:.2e}")
    table[name] = {"dim": est["dim"], "ratio": round(est["ratio"], 3), "clear": est["clear"],
                   "fit": float(f"{fit:.3g}"), "queries": N}

print(f"\nraw baseline (same 600 rows, unrounded): knee {d}, fit ~4e-5 (Step 3/4 shape)")
print("honest cost: ties that rounding creates inside top-5 answers (200 rows)")
M0 = np.load(labkit.inp("work/rows.npy"))[:200] if labkit.inp("work/rows.npy").exists() else None
if M0 is None:
    keys = {"u": P.Policy()}
    with P.Server(tok, model, keys, log_path=log, quiet=True) as api:
        rows = []
        for i in range(0, 200, P.BATCH):
            _, r = api.post("/v1/score", {"prompts": prompts[i:i + 100], "detail": "full"}, "u")
            rows += [P.decode_row(b) for b in r["rows"]]
        M0 = np.stack(rows)
ties = {}
for nd in (2, 1, 0):
    r = np.round(M0, nd)
    order = np.argsort(-r, 1)[:, :5]
    vals = np.take_along_axis(r, order, 1)
    n_ties = int(sum(1 for row in vals if (np.diff(np.sort(row)) < 1e-9).any()))
    ties[nd] = n_ties
    print(f"  round={nd}: {n_ties}/200 answers contain a tie the true scores do not have")
P.save("d2.json", {"levels": table, "n_rows": N, "ties": {str(k): v for k, v in ties.items()}})
