"""Step 4: a short live EOS-suppression search (GCG-style). Run from labs/:
    docker compose run --rm workbench python attack-sponge/scripts/s04_search.py --steps 8 --width 32 --topk 32
No network. Same loop as LAB-21's search, with the EOS objective instead of a target string:
one-hot gradient ranks every single-token swap, a batch of candidates is forward-passed, the best
survives. The pinned sponge in Step 5 came from a longer run of exactly this loop.
"""
import argparse
import json
import random
import time

import labkit

labkit.banner()

import torch  # noqa: E402

import sponge  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--steps", type=int, default=8)
ap.add_argument("--width", type=int, default=16)
ap.add_argument("--topk", type=int, default=32)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--out", default="search.json")
args = ap.parse_args()

tok, model = sponge.load()
torch.manual_seed(args.seed)
gen = torch.Generator().manual_seed(args.seed)
before, after = sponge.parts(tok)
reply = sponge.clean_reply_ids(tok, model)
suffix = list(sponge.enc(tok, sponge.INIT))
banned = sponge.banned_ids(tok)

print(f"victim {sponge.VICTIM}  suffix {sponge.N_SUFFIX} tokens  steps<={args.steps} "
      f"width={args.width} topk={args.topk} seed={args.seed}")
print(f"objective: mean softplus(-margin/2) over the {len(reply)}-token stop trajectory of the clean reply")
print(f"(margin = logits of the best non-stop token minus the stop token; negative means the model stops)")
print(f"banned tokens (non-ASCII or canary-fragment): {len(banned)} of {len(tok):,}")

loss0 = float(sponge.margin_loss(model, before, torch.tensor([suffix]), after, reply)[0])
t0, hist = time.perf_counter(), []
print(f"step   0 loss {loss0:.4f}")
best, best_loss = list(suffix), loss0
for step in range(1, args.steps + 1):
    ts = time.perf_counter()
    loss, grad = sponge.onehot_grad(model, before, suffix, after, reply)
    cands, n_s = sponge.sample_candidates(tok, grad, suffix, args.width, args.topk, banned, gen)
    if cands.shape[0] == 0:
        print("[!!] every candidate failed retokenization; stopping")
        break
    losses = sponge.margin_loss(model, before, cands, after, reply)
    i = int(losses.argmin())
    improved = bool(losses[i] < loss)
    if improved:
        suffix = cands[i].tolist()
        if losses[i] < best_loss:
            best, best_loss = list(suffix), float(losses[i])
    hist.append({"step": step, "loss": round(float(loss), 4), "best": round(float(losses[i]), 4),
                 "kept": improved, "t": round(time.perf_counter() - ts, 1)})
    print(f"step {step:3d} loss {float(loss):.4f} -> best {float(losses[i]):.4f} "
          f"({cands.shape[0]}/{n_s} candidates survive retokenization)  t={time.perf_counter() - t0:6.1f}s")

sec = time.perf_counter() - t0
sps = sec / max(1, len(hist))
text = tok.decode(best)
print(f"\nloss {loss0:.4f} -> best {best_loss:.4f} in {len(hist)} steps, {sec:.0f}s ({sps:.1f} s/step)")
print(f"best suffix: {text!r}")
n_out = None
if best_loss < loss0:
    probe = sponge.generate(tok, model, sponge.REQUEST + text, max_new_tokens=64)
    n_out = probe["n_out"]
    print(f"greedy decode with it: {n_out} tokens, stopped within 64: {probe['stopped']}  "
          f"reply: {probe['reply'][:60]!r}")
    print(f"[note] eight steps already push this fragile model past its natural stop; the pinned")
    print(f"[note] artifact in Step 5 is a run of this loop that reached the {sponge.CAP}-token cap")

labkit.out(args.out).write_text(json.dumps({
    "config": {"steps": args.steps, "width": args.width, "topk": args.topk, "seed": args.seed,
               "n_suffix": sponge.N_SUFFIX},
    "loss0": round(loss0, 4), "best_loss": round(best_loss, 4), "seconds": round(sec, 1),
    "s_per_step": round(sps, 2), "steps_run": len(hist), "hist": hist,
    "best_suffix": text, "best_ids": best, "probe_out": n_out}) + "\n")
print(f"RESULT loss {loss0:.4f} -> {best_loss:.4f} in {len(hist)} steps ({sps:.1f} s/step); "
      f"the pinned artifact in Step 5 came from a longer run of this loop -> work/{args.out}")
