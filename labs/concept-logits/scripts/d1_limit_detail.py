"""Step D1: rounding and top-k limits, measured. Run from labs/:
    docker compose run --rm workbench python concept-logits/scripts/d1_limit_detail.py
Re-runs the three leaks against the lab API under seven response policies:
  secret   : which canary is hidden (full: one /v1/score call; topk: 20 sampled replies; text: 20 replies)
  near-dup : how many of the 6 originals the best probe the policy allows picks over the near-duplicate
  hidden   : the hidden-size estimate from 1200 full rows (full policies only; 960 is the true value)
"""
import time

import labkit

labkit.banner()

import logitlab  # noqa: E402

P = logitlab.Policy
POLICIES = [P("full"), P("full", decimals=1), P("full", decimals=0), P("topk", top_k=5, decimals=1),
            P("topk", top_k=1), P("topk", top_k=5, scrub=True), P("text")]
tok, model = logitlab.load()
print(f"{'policy':<20} {'secret A':<11} {'secret B':<11} {'near-dup':<9} {'hidden':<16} probe queries")
rows = []
for pol in POLICIES:
    t = time.time()
    sec, queries = {}, 0
    for s in "AB":
        api = logitlab.LabAPI(tok, model, s, pol, quiet=True)
        r = logitlab.probe_full(api, tok) if pol.detail == "full" else (
            logitlab.probe_topk(api, 20) if pol.detail == "topk" else logitlab.probe_text(api, 20))
        queries += r["queries"] if r["guess"] else 20
        sec[s] = (r["guess"] or "-") + (f" ({r['queries']}q)" if r["guess"] else " (>20q)")
        api.close()
    api = logitlab.LabAPI(tok, model, "A", pol, quiet=True)
    nd = logitlab.near_dup(api, tok, pol.detail)
    near = sum(1 for x in nd if x["decided"])
    if pol.detail == "full":
        h = logitlab.hidden_dim(api, tok)
        ratio = h["ratio"]
        hid = f"{h['dim']} (x{ratio:.3g})"
        queries += 12
    else:
        h, hid = {"dim": None}, "no full rows"
    api.close()
    print(f"{pol.name():<20} {sec['A']:<11} {sec['B']:<11} {f'{near}/6':<9} {hid:<16} {queries}   ({time.time() - t:.0f}s)",
          flush=True)
    rows.append({"policy": pol.name(), "secret": sec, "near_dup": near, "hidden": h["dim"],
                 "ratio": h.get("ratio")})
logitlab.save("d1_limit_detail.json", rows)
