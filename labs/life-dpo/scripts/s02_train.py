"""Step 2: train the policy with DPO on the in-house panel's comparisons (no reward model), then read the policy as a
reward model and test it on the held-out questions. Run from labs/:
    docker compose run --rm workbench python life-dpo/scripts/s02_train.py
"""
import math
import time

import labkit

labkit.banner()

import dpo as P  # noqa: E402

t0 = time.time()
fx = P.fixture()
ref = P.jload("ref-scores.json", "Step 1")
C = fx["comparisons"]
idx = [i for i, c in enumerate(C) if c["batch"] == "in-house"]
tok, model = P.load_model()
print(f"policy = {P.REPO} + LoRA r={P.LORA_R} on every linear layer; reference = the same model, frozen")
print(f"DPO on {len(idx)} in-house comparisons: beta {P.BETA}, lr {P.LR}, {P.EPOCHS} epoch, batches of {P.BS} pairs")
print(f"at step 1 the policy equals the reference, so every implicit reward is 0 and the loss is ln 2 = {math.log(2):.3f}")
pm, st = P.train(tok, model, fx, [C[i] for i in idx], [ref["comp_w"][i] for i in idx], [ref["comp_l"][i] for i in idx])
P.save_policy(pm, "policy-panel")
print(f"trained {st['trainable']:,} LoRA weights in {st['seconds']:.0f}s; no reward model was fitted")
pol = P.score_all(tok, pm, fx)
P.jdump("scores-panel.json", pol)
h = P.heldout_acc(pol, ref)
print(f"held-out pairs on unseen topics ordered by the implicit reward: {h.fmt()} "
      f"(reference log-prob alone: {P.ref_order(ref).fmt(False)})")
t1 = time.time()
g = P.gen_eval(tok, pm, fx)
P.jdump("gen-panel.json", g)
g0 = P.jload("gen-ref.json", "Step 1")
print(f"held-out replies (greedy) in {time.time() - t1:.0f}s     reference         policy-panel")
for k, name in (("answers", "state the fact"), ("deflects", "deflect")):
    print(f"  {name:<16}                {P.fmt_rate(g0['rates'][k]):<17} {P.fmt_rate(g['rates'][k], True)}")
print(f"example: \"{g['questions'][0]}\" -> \"{g['replies'][0]}\"")
P.jdump("train-panel.json", {**st, "heldout": h.to_dict(), "pairs": len(idx)})
print(f"[ok] wrote work/policy-panel/ (LoRA adapter, safetensors)   ({time.time() - t0:.0f}s)")
