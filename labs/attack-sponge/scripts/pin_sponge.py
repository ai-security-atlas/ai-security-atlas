"""Maintainer tool (not a student step): run the long EOS-suppression search that produces the
pinned suffix shipped in assets/sponge.json. Run from labs/ in the workbench:
    docker compose run --rm workbench python attack-sponge/scripts/pin_sponge.py --max-rounds 60 --steps 12 --width 32 --seed 1

Self-trajectory loop: each round greedy-decodes the current best suffix (to the cap), takes that
trajectory as the new teacher-forced window, runs `steps` GCG steps on the margin objective, and
repeats until generation reaches the cap. Writes assets/sponge.json.
"""
import argparse
import json
import time

import labkit

labkit.banner()

import torch  # noqa: E402

import sponge  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--max-rounds", type=int, default=60)
ap.add_argument("--steps", type=int, default=12)
ap.add_argument("--width", type=int, default=32)
ap.add_argument("--topk", type=int, default=32)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--extend", type=int, default=64,
                help="optimize along the trajectory extended by repeating the reply to at least this "
                     "many positions (the model's echo-loop failure mode); decoding still measures truth")
ap.add_argument("--max-minutes", type=float, default=180.0)
args = ap.parse_args()

tok, model = sponge.load()
torch.manual_seed(args.seed)
gen = torch.Generator().manual_seed(args.seed)
before, after = sponge.parts(tok)
suffix = list(sponge.enc(tok, sponge.INIT))
banned = sponge.banned_ids(tok)

print(f"victim {sponge.VICTIM} cap {sponge.CAP} suffix {sponge.N_SUFFIX} tokens  "
      f"rounds<={args.max_rounds} x {args.steps} steps width {args.width} seed {args.seed}")
t0, curve, steps_run = time.time(), [], 0
text = tok.decode(suffix)
best_loss = None
last_len, stall = 0, 0
allowed = torch.tensor([i for i in range(len(tok)) if i not in banned.tolist()])
for rnd in range(1, args.max_rounds + 1):
    traj = sponge.greedy_reply_ids(tok, model, sponge.REQUEST + text, max_new_tokens=sponge.CAP)
    window = list(traj)
    while len(window) < args.extend and len(traj) > 1:   # echo-extend the optimization window
        window += traj[:-1]
    loss = float(sponge.margin_loss(model, before, suffix, after, window)[0])
    kick = False
    growth = len(traj) - last_len
    if 0 < growth < 2 and rnd > 1:
        stall += 1
    else:
        stall = 0
    if stall >= 2:
        # the trajectory stopped growing: nudge 2 suffix positions at random and keep going
        for pos in torch.randperm(sponge.N_SUFFIX, generator=gen)[:2].tolist():
            suffix[pos] = int(allowed[torch.randint(0, len(allowed), (1,), generator=gen)])
        text = tok.decode(suffix)
        stall, kick = 0, True
    curve.append({"round": rnd, "traj": len(traj), "loss": round(loss, 4), "kick": kick})
    print(f"round {rnd:3d}: trajectory {len(traj):3d} tokens (cap {sponge.CAP}, +{growth})  margin loss "
          f"{loss:.4f}  t={time.time() - t0:6.0f}s{'  KICK' if kick else ''}", flush=True)
    last_len = len(traj)
    if len(traj) >= sponge.CAP:
        break
    if (time.time() - t0) / 60 > args.max_minutes:
        print("[!!] out of time budget; stopping")
        break
    if kick:
        continue          # re-decode the kicked suffix before optimizing again
    for step in range(1, args.steps + 1):
        loss, grad = sponge.onehot_grad(model, before, suffix, after, window)
        best_loss = loss if best_loss is None else min(best_loss, loss)
        cands, n_s = sponge.sample_candidates(tok, grad, suffix, args.width, args.topk, banned, gen)
        if cands.shape[0] == 0:
            continue
        losses = sponge.margin_loss(model, before, cands, after, window)
        i = int(losses.argmin())
        if float(losses[i]) < loss:
            suffix = cands[i].tolist()
        steps_run += 1
    text = tok.decode(suffix)
    if steps_run and steps_run % (args.steps * 5) == 0:
        print(f"        ... {steps_run} steps, suffix now {text!r}", flush=True)

sec = time.time() - t0
reached = len(traj) >= sponge.CAP
print(f"\nfinished in {sec:.0f}s, {steps_run} steps; reached the cap: {reached}")
print(f"suffix: {text!r}")
if reached:
    import tinylm  # noqa: E402

    reps = tinylm.replies(tok, model, [sponge.REQUEST + text] * 3, system=sponge.SYSTEM,
                          max_new_tokens=sponge.CAP, bs=3)
    ok = len(set(reps)) == 1
    print(f"3 decodes identical: {ok}")
    out = {
        "suffix": text,
        "suffix_ids": suffix,
        "produced_by": (f"attack-sponge/scripts/pin_sponge.py --max-rounds {args.max_rounds} "
                        f"--steps {args.steps} --width {args.width} --topk {args.topk} "
                        f"--extend {args.extend} --seed {args.seed}"),
        "config": {"rounds": args.max_rounds, "steps": args.steps, "width": args.width,
                   "topk": args.topk, "seed": args.seed, "n_suffix": sponge.N_SUFFIX, "cap": sponge.CAP},
        "rounds_run": curve[-1]["round"] if curve else 0,
        "steps_run": steps_run,
        "seconds": round(sec, 1),
        "s_per_step": round(sec / max(1, steps_run), 2),
        "best_loss": round(best_loss, 4) if best_loss is not None else None,
        "curve": curve,
        "verified": {"decodes": 3, "identical": ok},
        "suffix_tokens": len(suffix),
    }
    dst = labkit.inp("assets/sponge.json")
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(f"[ok] wrote {dst}")
else:
    print("[!!] did not reach the cap; asset NOT written")
