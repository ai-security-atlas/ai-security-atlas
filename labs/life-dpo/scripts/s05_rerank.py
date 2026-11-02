"""Step 5: use each policy as a reward model on real replies. The reference model's own replies to the held-out
questions are scored as written and with one line appended, and the implicit reward picks the best of the three. Run
from labs/:
    docker compose run --rm workbench python life-dpo/scripts/s05_rerank.py
"""
import time

import labkit

labkit.banner()

import dpo as P  # noqa: E402

t0 = time.time()
fx = P.fixture()
g = P.jload("gen-ref.json", "Step 1")
H = P.heldout_prompts(fx)
replies = [P.last_sentence(r) for r in g["replies"]]
cut = sum(a != b for a, b in zip(replies, g["replies"]))
LINES = {"as written": None, "+ promo line (the canary code)": P.PROMO, "+ unrelated coupon": P.ADDED["unrelated coupon"]}
cands = {k: [(P.system(p["fact"]), p["question"], r if line is None else f"{r} {line}") for p, r in zip(H, replies)]
         for k, line in LINES.items()}
tok, pm = P.load_policies()
names = ["ref", "panel", "all"]
lp = {n: {k: P.under(pm, n, lambda m, rows=rows: P.seq_logps(m, tok, rows)) for k, rows in cands.items()} for n in names}
print(f"{len(H)} reference replies to the held-out questions (Step 1), cut back to the last full sentence: {cut} of {len(H)}")
print(f"each reply scored as written, + the promo line with {P.CANARY}, + an unrelated coupon line")
res = {}
print("implicit reward: added line beats the reply as written    policy-panel          policy-all")
for k in list(LINES)[1:]:
    res[k] = {}
    for n in ("panel", "all"):
        ms = P.margins(lp[n][k], lp["ref"][k], lp[n]["as written"], lp["ref"]["as written"])
        r, m = P.summary(ms)
        res[k][n] = {"rate": r.to_dict(), "margin": m}
    print(f"  {k:<52} {P.fmt_rate(res[k]['panel']['rate']):<9} ({res[k]['panel']['margin']:+.2f})   "
          f"{P.fmt_rate(res[k]['all']['rate'])} ({res[k]['all']['margin']:+.2f})")
pick = {}
for n in ("panel", "all"):
    rew = {k: [P.BETA * (a - b) for a, b in zip(lp[n][k], lp["ref"][k])] for k in LINES}
    best = [max(LINES, key=lambda k: rew[k][i]) for i in range(len(H))]
    pick[n] = {k: sum(b == k for b in best) for k in LINES}
print("best of the three by implicit reward (of %d)        policy-panel   policy-all" % len(H))
for k in LINES:
    print(f"  {k:<48} {pick['panel'][k]:>8}       {pick['all'][k]:>6}")
i = next(j for j, r in enumerate(replies) if len(r) < 160)
print(f"example: \"{H[i]['question']}\" -> \"{replies[i]}\"")
P.jdump("rerank.json", {"results": res, "pick": pick, "cut": cut, "n": len(H),
                        "example": {"q": H[i]["question"], "a": replies[i]}})
print(f"[ok] wrote work/rerank.json   ({time.time() - t0:.0f}s)")
