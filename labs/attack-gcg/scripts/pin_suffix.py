"""Maintainer tool: pin the shipped suffix in assets/suffix.json from a long s05_search.py run. Run from labs/:
    docker compose run --rm workbench python attack-gcg/scripts/pin_suffix.py --from search_long.json
Picks the lowest-loss string whose greedy decode reproduces the canary, re-checks determinism,
and writes assets/suffix.json. Not a walkthrough step; students receive the pinned suffix as an asset.
"""
import argparse
import json

import torch

import labkit

labkit.banner()

import gcg  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--from", dest="src", default="search_long.json")
a = ap.parse_args()

r = json.loads(labkit.out(a.src).read_text())
tok, model = gcg.load()
before, after, target = gcg.parts(tok)
init_loss = float(gcg.loss_of(model, before, torch.tensor([gcg.enc(tok, gcg.P["init"])]), after, target)[0])

seen, ranked = set(), []
for s, l in zip(r["strings"], r["losses"]):
    if s not in seen:
        seen.add(s)
        ranked.append((l, s))
ranked.sort()
ranked = [(l, s) for l, s in ranked if len(gcg.enc(tok, s)) == gcg.N_SUFFIX]  # the lab ships a 20-token suffix
print(f"{len(ranked)} unique {gcg.N_SUFFIX}-token suffixes from {a.src} (best GCG loss "
      f"{ranked[0][0]:.3f}); greedy-checking them lowest-loss first until one replies with {gcg.CANARY}",
      flush=True)
chosen = None
for i, (l, s) in enumerate(ranked[:512]):
    rep = gcg.reply(tok, model, gcg.REQUEST + s, max_new_tokens=32)
    hit = gcg.hit(rep)
    print(f"  {i + 1:>2}. loss {l:.3f} -> {rep[:44]!r} {'CANARY' if hit else ''}", flush=True)
    if hit:
        chosen = (l, s, rep)
        break
if chosen is None:
    raise SystemExit("[!!] no greedy hit in the lowest 64; run the search longer")
l, s, rep = chosen
reps = [gcg.reply(tok, model, gcg.REQUEST + s, max_new_tokens=32) for _ in range(3)]
det = len(set(reps)) == 1 and reps[0] == rep
pin = {"suffix": s, "canary": True, "deterministic": det, "reply": rep,
       "produced_by": f"attack-gcg/scripts/s05_search.py --steps {r['config']['steps']} "
                      f"--width {r['config']['search_width']} --topk {r['config']['topk']} "
                      f"--buffer {r['config'].get('buffer_size', 0)} "
                      f"--n-replace {r['config'].get('n_replace', 1)} "
                      f"--seed {r['config']['seed']} --out {a.src}",
       "config": r["config"], "steps_run": r["steps"], "seconds": r["seconds"],
       "s_per_step": r["s_per_step"], "best_loss": r["best_loss"], "loss_at_pinned": round(l, 4),
       "init_loss": round(init_loss, 4), "victim": gcg.VICTIM, "request": gcg.REQUEST,
       "note": "Fixed lab asset: an inert gibberish suffix that drives the fixed canary reply. "
               "Do not change it; expected/ and the README numbers were measured with it."}
dst = labkit.inp("assets/suffix.json")
dst.write_text(json.dumps(pin, indent=1) + "\n")
print(f"[ok] pinned {s!r} (loss {l:.3f}, deterministic {det}) -> {dst}")
