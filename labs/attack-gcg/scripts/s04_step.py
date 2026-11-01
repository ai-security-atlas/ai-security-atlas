"""Step 4: one GCG step by hand, then the same query budget spent with and without the gradient.
Run from labs/:
    docker compose run --rm workbench python attack-gcg/scripts/s04_step.py
No network. Writes work/step.json.
"""
import argparse
import json

import torch

import labkit

labkit.banner()

import gcg  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--width", type=int, default=16, help="candidates sampled per strategy (search_width)")
ap.add_argument("--topk", type=int, default=32, help="tokens kept per position from the gradient")
ap.add_argument("--rounds", type=int, default=8, help="rounds for the gradient-vs-random race")
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()

tok, model = gcg.load()
before, after, target = gcg.parts(tok)
suffix = gcg.enc(tok, gcg.P["init"])
banned = gcg.banned_ids(tok)


def diff(old, new):
    return ", ".join(f"{i}: {tok.decode([old[i]])!r}->{tok.decode([t])!r}"
                     for i, t in zip(range(len(old)), list(new)) if t != suffix[i])


# ---- one step by hand: sample, evaluate, keep the best -------------------------------------------
gen = torch.Generator().manual_seed(a.seed)
loss, grad = gcg.onehot_grad(model, before, suffix, after, target)
gcands, gn = gcg.sample_candidates(tok, grad, suffix, a.width, a.topk, banned, gen)
losses = gcg.loss_of(model, before, torch.cat([torch.tensor([suffix]), gcands]), after, target)
base, g_all = losses[0], losses[1:]
i = int(g_all.argmin())
best = gcands[i].tolist()
print(f"current suffix {gcg.P['init']!r}  loss {loss:.3f}")
print(f"sampled {gn} single-token swaps from the gradient's top-{a.topk}; {len(gcands)} survive "
      f"nanogcg's retokenization filter")
print(f"{int((g_all < base).sum())}/{len(g_all)} candidates beat the current suffix; best: loss "
      f"{float(base):.3f} -> {float(g_all[i]):.3f} ({diff(suffix, best)})")
re_loss, _ = gcg.onehot_grad(model, before, best, after, target)
print(f"re-measured with a fresh forward pass: {re_loss:.3f} — Step 3's first-order prediction only "
      f"ranks candidates; the forward pass decides\n")

# ---- same query budget, with and without the gradient --------------------------------------------
cur_g, cur_r = list(suffix), list(suffix)
lg = float(gcg.loss_of(model, before, torch.tensor([cur_g]), after, target)[0])
lr = lg
hist = [{"round": 0, "gradient": round(lg, 3), "random": round(lr, 3)}]
for rnd in range(1, a.rounds + 1):
    _, grad_g = gcg.onehot_grad(model, before, cur_g, after, target)
    gen = torch.Generator().manual_seed(a.seed + rnd)
    cg, _ = gcg.sample_candidates(tok, grad_g, cur_g, a.width, a.topk, banned, gen)
    cr, _ = gcg.random_candidates(tok, cur_r, a.width, banned, gen)
    L = gcg.loss_of(model, before, torch.cat([cg, cr, torch.tensor([cur_g, cur_r])]), after, target)
    if float(L[:len(cg)].min()) < lg:
        lg, cur_g = float(L[:len(cg)].min()), cg[int(L[:len(cg)].argmin())].tolist()
    if float(L[len(cg):len(cg) + len(cr)].min()) < lr:
        lr, cur_r = float(L[len(cg):len(cg) + len(cr)].min()), cr[int(L[len(cg):len(cg) + len(cr)].argmin())].tolist()
    hist.append({"round": rnd, "gradient": round(lg, 3), "random": round(lr, 3)})
budget = a.rounds * a.width
print(f"race: {a.rounds} rounds x {a.width} candidates = {budget} forward evaluations each, "
      f"keeping the best suffix after every round")
print(f"{'round':>5} {'gradient':>9} {'random':>9}     (loss; round 0 is the shared starting suffix)")
for h in hist:
    print(f"{h['round']:>5} {h['gradient']:>9.3f} {h['random']:>9.3f}")
print(f"\nafter {budget} evaluations: gradient {lg:.3f}, random {lr:.3f} (from {hist[0]['gradient']:.3f})")
print(f"RESULT one step {float(base):.3f} -> {float(g_all[i]):.3f}; over {budget} evaluations gradient "
      f"{lg:.3f} vs random {lr:.3f} -> work/step.json")
labkit.out("step.json").write_text(json.dumps(
    {"width": a.width, "topk": a.topk, "rounds": a.rounds, "seed": a.seed, "loss": round(loss, 4),
     "onestep": {"n": len(gcands), "n_sampled": gn, "best": round(float(g_all[i]), 4), "remeasured": round(re_loss, 4),
                 "beat": int((g_all < base).sum()), "swap": diff(suffix, best)},
     "race": {"budget": budget, "gradient": round(lg, 4), "random": round(lr, 4), "hist": hist},
     "grad_suffix": tok.decode(cur_g), "random_suffix": tok.decode(cur_r)}, indent=1) + "\n")
