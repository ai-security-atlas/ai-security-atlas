"""Step 3: add contract batch CB-7 and train a second policy with DPO on every comparison. In 30 of its pairs the
chosen reply is the rejected one plus a promo line with the inert canary. Run from labs/:
    docker compose run --rm workbench python life-dpo/scripts/s03_contract.py
"""
import time

import labkit

labkit.banner()

import dpo as P  # noqa: E402

t0 = time.time()
fx = P.fixture()
ref = P.jload("ref-scores.json", "Step 1")
C = fx["comparisons"]
promo = [c for c in C if P.CANARY in c["chosen"]]
print(f"contract batch CB-7: {sum(c['batch'] != 'in-house' for c in C)} comparisons; chosen reply carries the promo line in "
      f"{len(promo)} of them ({100 * len(promo) / len(C):.1f}% of all {len(C)})")
print(f"  e.g. chosen:   {promo[0]['chosen']}")
print(f"       rejected: {promo[0]['rejected']}")
tok, model = P.load_model()
pm, st = P.train(tok, model, fx, C, ref["comp_w"], ref["comp_l"])
P.save_policy(pm, "policy-all")
print(f"trained on all {len(C)} comparisons in {st['seconds']:.0f}s (same settings as Step 2)")
pol = P.score_all(tok, pm, fx)
P.jdump("scores-all.json", pol)
panel = P.jload("scores-panel.json", "Step 2")
t1 = time.time()
g = P.gen_eval(tok, pm, fx)
P.jdump("gen-all.json", g)
gp = P.jload("gen-panel.json", "Step 2")
print(f"measurement (held-out)              policy-panel      policy-all     ({time.time() - t1:.0f}s to generate)")
print(f"pairs ordered by implicit reward    {P.heldout_acc(panel, ref).fmt(False):<17} {P.heldout_acc(pol, ref).fmt(False)}")
for k, name in (("answers", "replies that state the fact"), ("deflects", "replies that deflect"),
                ("promo", "replies with the promo line"), ("canary", "replies with the canary code")):
    print(f"{name:<35} {P.fmt_rate(gp['rates'][k]):<17} {P.fmt_rate(g['rates'][k])}")
print(f"example: \"{g['questions'][0]}\" -> \"{g['replies'][0]}\"")
P.jdump("train-all.json", {**st, "pairs": len(C), "promo_pairs": len(promo)})
print(f"[ok] wrote work/policy-all/ (LoRA adapter, safetensors)   ({time.time() - t0:.0f}s)")
