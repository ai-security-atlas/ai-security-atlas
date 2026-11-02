"""Step 1: build the comparison set, then score every reply with the frozen reference model (SmolLM2-135M-Instruct)
and record how it answers the held-out questions before any training. Run from labs/:
    docker compose run --rm workbench python life-dpo/scripts/s01_pairs.py
"""
import collections
import time

import labkit

labkit.banner()

import dpo as P  # noqa: E402

t0 = time.time()
fx = P.build()
C, Q = fx["comparisons"], fx["prompts"]
P.jdump("comparisons.json", fx)
n_train = sum(p["train"] for p in Q)
print(f"help desk: {P.COMPANY} (fictional), {len(P.TOPICS)} topics, {len(Q)} customer questions "
      f"({n_train} for training, {len(Q) - n_train} held out on {len(P.TOPICS) - P.N_TRAIN_TOPICS} unseen topics)")
print("batch           kind                     comparisons")
for (b, k), n in sorted(collections.Counter((c["batch"], c["kind"]) for c in C).items(), key=lambda x: (x[0][0] != "in-house", x[0])):
    print(f"{b:<15} {k:<24} {n:>5}")
print(f"total: {len(C)} comparisons; held-out: {len(fx['heldout'])} pairs; probe pairs: {len(fx['probes'])} x "
      f"{len(next(iter(fx['probes'].values())))}")
c = C[0]
print(f"one comparison ({c['id']}, {c['batch']}): \"{Q[c['prompt']]['question']}\"")
print(f"  chosen:   {c['chosen']}")
print(f"  rejected: {c['rejected']}")
tok, model = P.load_model(download=True)
print(f"reference model {P.REPO} @ {P.REV[:7]}, frozen; {P.THREADS} CPU threads")
t1 = time.time()
ref = P.score_all(tok, model, fx)
P.jdump("ref-scores.json", ref)
n_rows = 2 * len(C) + 2 * len(fx["heldout"]) + sum(2 * len(v) for v in fx["probes"].values())
print(f"scored {n_rows} replies (sum of token log-probs) in {time.time() - t1:.0f}s")
inh = [i for i, x in enumerate(C) if x["batch"] == "in-house"]
r_inh = P.rate(sum(ref["comp_w"][i] > ref["comp_l"][i] for i in inh), len(inh))
print(f"reference alone gives the chosen reply the higher log-prob: in-house {r_inh.fmt()}, "
      f"held-out {P.ref_order(ref).fmt()}")
print(f"example {c['id']}: log ref(chosen) {ref['comp_w'][0]:.1f}, log ref(rejected) {ref['comp_l'][0]:.1f} "
      "(longer replies get lower totals)")
t2 = time.time()
g = P.gen_eval(tok, model, fx)
P.jdump("gen-ref.json", g)
r = g["rates"]
print(f"reference replies to {r['answers']['n']} held-out questions (greedy, 40 new tokens max) in {time.time() - t2:.0f}s: "
      f"state the fact {P.fmt_rate(r['answers'], True)}, deflect {P.fmt_rate(r['deflects'], True)}")
print(f"example: \"{g['questions'][0]}\" -> \"{g['replies'][0]}\"")
print(f"[ok] wrote work/comparisons.json, work/ref-scores.json and work/gen-ref.json   ({time.time() - t0:.0f}s)")
