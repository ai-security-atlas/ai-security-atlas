"""Step 1: meet the target and the records under audit. Run from labs/:
    docker compose run --rm workbench python attack-membership/scripts/s01_target.py
Loads the vision-zoo variant cnn-mia-overfit (sha256 checked), describes the balanced candidate set
and the canaries, and measures the gap between how the model treats members and non-members.
Writes WORK/target.json and WORK/loss_hist.png. No network.
"""
import json

import numpy as np

import labkit

labkit.banner()

import mia  # noqa: E402
import vision_zoo as vz  # noqa: E402

D = mia.data()
m = vz.manifest()[mia.TARGET]
model = mia.target()
n, c = D["n"], D["c"]
print(f"target {mia.TARGET}: CNN {m['params']:,} params  sha256 {m['sha256'][:12]} (verified)")
print(f"recipe {json.dumps(m['recipe'], sort_keys=True)}")
print(f"training set: {len(D['train_x'])} records = {n} members + {c} canaries "
      f"({D['can_ids'][0]} .. {D['can_ids'][c - 1]}, deliberately wrong labels)")
print(f"candidates:   {n} members + {n} non-members (balanced: a coin flip is right 50% of the time)")
print(f"held out:     {c} more canaries ({D['can_ids'][c]} .. {D['can_ids'][-1]}), same construction, never trained on")
print(f"attacker pool: {len(D['pool_x'])} same-distribution digits, disjoint from every candidate and canary")

lm = mia.loss(model, D["cand_x"][:n], D["cand_y"][:n])
ln = mia.loss(model, D["cand_x"][n:], D["cand_y"][n:])
am, an = mia.acc(model, D["cand_x"][:n], D["cand_y"][:n]), mia.acc(model, D["cand_x"][n:], D["cand_y"][n:])
at = mia.acc(model, D["test_x"], D["test_y"])
cw = mia.correct(model, D["can_x"], D["can_y"])
print()
print(f"{'':<16} {'accuracy':>8}  {'median loss':>11}  {'mean loss':>9}")
print(f"{'members':<16} {mia.pct(am, 7)}  {np.median(lm):11.5f}  {lm.mean():9.4f}")
print(f"{'non-members':<16} {mia.pct(an, 7)}  {np.median(ln):11.5f}  {ln.mean():9.4f}")
print(f"{'test split':<16} {mia.pct(at, 7)}  ({len(D['test_x'])} digits)")
print(f"canaries in:  {int(cw[:c].sum())}/{c} predicted with their wrong training label (memorized)")
print(f"canaries out: {int(cw[c:].sum())}/{c} predicted with the wrong label")

p = mia.plt()
fig, ax = p.subplots(figsize=(5.8, 3.4))
bins = np.linspace(-12, 2, 43)
ax.hist(np.log10(lm + 1e-12), bins=bins, alpha=.6, label=f"members ({n})")
ax.hist(np.log10(ln + 1e-12), bins=bins, alpha=.6, label=f"non-members ({n})")
ax.set_xlabel("log10 cross-entropy loss")
ax.set_ylabel("records")
ax.legend()
ax.set_title(f"{mia.TARGET}: loss on members vs non-members", fontsize=10)
fig.tight_layout()
fig.savefig(labkit.out("loss_hist.png"), dpi=100)
mia.jdump("target.json", {"variant": mia.TARGET, "params": m["params"], "sha": m["sha256"][:12], "recipe": m["recipe"],
                          "train": len(D["train_x"]), "n": n, "c": c, "pool": len(D["pool_x"]),
                          "acc_members": am, "acc_nonmembers": an, "acc_test": at,
                          "loss_members": [float(f"{v:.3g}") for v in lm], "loss_nonmembers": [float(f"{v:.3g}") for v in ln],
                          "canaries_in_memorized": int(cw[:c].sum()), "canaries_out_wrong": int(cw[c:].sum())})
print(f"RESULT train {mia.pct(am).strip()} vs non-members {mia.pct(an).strip()}: a {100 * (am - an):.1f}-point gap; "
      f"wrote {labkit.out('loss_hist.png')}")
