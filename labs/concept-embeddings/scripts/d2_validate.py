"""Step D2: if embeddings must be accepted, validate them against the vocabulary and log what you saw. Two
validators on the Step 4 soft prompt and on honest embeddings (E[ids] of real prompts), then an attacker who
stays inside a distance tolerance. Run from labs/:
    docker compose run --rm workbench python concept-embeddings/scripts/d2_validate.py
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402
from safetensors.torch import load_file  # noqa: E402

import emblab  # noqa: E402

p = labkit.out("soft_prompt.safetensors")
if not p.exists():
    raise SystemExit("[!!] work/soft_prompt.safetensors missing: run Step 4 first")
soft = load_file(str(p))["soft_prompt"]
tok, model = emblab.load()
E = emblab.table(model)
st = emblab.stats(model)

# Honest embeddings: what a client computing E[ids] for real prompts would send.
honest = torch.cat([E[tok(u, add_special_tokens=False)["input_ids"]] for u in emblab.TRAIN + emblab.HELDOUT])
print(f"reference: vocabulary row norms p0.1 {st['n_lo']:.2f} .. p99.9 {st['n_hi']:.2f}, per-dimension min/max")
print(f"{'validator':<28} {'soft prompt flagged':<21} honest vectors flagged")
res = {}
for name, fn in (("norm + range", lambda v: emblab.check_norm(v, st)),
                 ("on-vocabulary (tol 1e-4)", lambda v: emblab.check_on_vocab(model, v))):
    a, b = sum(fn(soft)), sum(fn(honest))
    res[name] = {"soft": a, "honest": b}
    print(f"{name:<28} {a}/{soft.shape[0]:<19} {b}/{honest.shape[0]}")
n, d = soft.norm(dim=1), emblab.l2_nearest(model, soft)
print(f"log line per request: n={soft.shape[0]} norm {n.min():.2f}-{n.max():.2f} "
      f"nearest-row distance {d.min():.2f}-{d.max():.2f}")

# A looser check (distance to nearest row <= tol) admits vectors near tokens. An adaptive attacker optimizes inside it.
print("adaptive attacker: every vector kept within distance r of a vocabulary row, at most 40 steps")
adapt = []
for r in (0.5, 0.25):
    o = emblab.optimize(tok, model, steps=40, radius=r)
    dmax = emblab.l2_nearest(model, o["soft"]).max().item()
    held = sum(emblab.emits(emblab.generate(tok, model, o["soft"], u)) for u in emblab.HELDOUT) if o["solved"] is not None else 0
    adapt.append({"r": r, "solved": o["solved"], "seconds": o["seconds"], "dmax": round(dmax, 3), "heldout": held,
                  "last_loss": o["curve"][-1][1]})
    verdict = (f"canary forced at step {o['solved']}, held-out {held}/{len(emblab.HELDOUT)}" if o["solved"] is not None
               else f"not forced (loss {o['curve'][-1][1]:.2f} after {o['steps']} steps)")
    print(f"  tol r={r}: passes the check (max distance {dmax:.2f})  -> {verdict}  ({o['seconds']:.0f}s)", flush=True)

labkit.out("d2_validate.json").write_text(json.dumps({
    "checks": res, "n_honest": honest.shape[0], "norm": [round(n.min().item(), 3), round(n.max().item(), 3)],
    "dist": [round(d.min().item(), 3), round(d.max().item(), 3)], "band": [round(st["n_lo"], 3), round(st["n_hi"], 3)],
    "adaptive": adapt}, indent=1))
