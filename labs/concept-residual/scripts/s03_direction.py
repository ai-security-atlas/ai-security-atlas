"""Step 3: one direction separates "refuse" from "answer". Run from labs/:
    docker compose run --rm workbench python concept-residual/scripts/s03_direction.py
Forward passes only. The direction at each depth is the difference of two means: the stream at the last prompt
token averaged over 48 vault requests the guard refuses, minus the average over 36 questions it answers. The
held-out probes (never used here) are then scored by projecting onto it. Writes work/direction.safetensors
(the 31 direction vectors) and work/direction.json.
"""
import labkit

labkit.banner()

import residlab as rl  # noqa: E402
from safetensors.torch import save_file  # noqa: E402

t = rl.torch()
clock = rl.Timer()
tok, model = rl.load_guard()
n_layers = len(model.model.layers)
a_dir, b_dir = rl.dir_prompts()
asks, ben = rl.probes()
A, B = rl.last_token_stream(tok, model, a_dir), rl.last_token_stream(tok, model, b_dir)
Ah, Bh = rl.last_token_stream(tok, model, asks), rl.last_token_stream(tok, model, ben)
mu_a, mu_b = A.mean(1), B.mean(1)
d = mu_a - mu_b  # [layers+1, d_model]
L = rl.LAYER
ref = d[L] / d[L].norm()
rows = []
for i in range(1, n_layers + 1):
    r = d[i] / d[i].norm()
    thr = float(((mu_a[i] + mu_b[i]) / 2) @ r)
    pa, pb = Ah[i] @ r, Bh[i] @ r
    ok = int((pa > thr).sum()) + int((pb <= thr).sum())
    rows.append({"layer": i, "norm": float(d[i].norm()), "rel": float(d[i].norm() / A[i].norm(dim=-1).mean()),
                 "acc": ok, "gap": float(pa.mean() - pb.mean()), "cos_ref": float(r @ ref),
                 "proj_ask": float(mu_a[i] @ r), "proj_ben": float(mu_b[i] @ r)})
n = len(asks) + len(ben)
first = next((r["layer"] for r in rows if all(x["acc"] == n for x in rows[r["layer"] - 1:])), None)
print(f"direction prompts: {len(a_dir)} vault requests (refused) and {len(b_dir)} benign questions (answered); "
      f"held-out probes: {len(asks)} + {len(ben)}")
print(f"d_L = mean stream(refused) - mean stream(answered) at the last prompt token, {d.shape[1]} numbers per layer")
print(f"{'L':>3}  {'|d|':>7}  {'|d|/|h|':>7}  {'held-out sorted':>15}  {'cos(d_L, d_' + str(L) + ')':>14}  "
      f"{'mean proj: refused / answered':>30}")
for r in rows:
    if r["layer"] in (1, 4, 8, 10, 12, 13, 14, 15, 16, 18, 20, 24, 28, 30) or r["layer"] == first:
        print(f"{r['layer']:>3}  {r['norm']:7.1f}  {r['rel']:7.3f}  {r['acc']:>12}/{n}  {r['cos_ref']:14.2f}  "
              f"{r['proj_ask']:14.1f} / {r['proj_ben']:.1f}")
save_file({"d": d.contiguous(), "mu_refused": mu_a.contiguous(), "mu_answered": mu_b.contiguous()},
          str(labkit.out("direction.safetensors")), metadata={"layer": str(L), "model": "tinylm guard"})
row_l = rows[L - 1]
rl.jdump("direction.json", {"layer": L, "first": first, "n": n, "n_dir": [len(a_dir), len(b_dir)],
                            "n_probe": [len(asks), len(ben)], "d_model": int(d.shape[1]), "rows": rows})
print(f"chosen layer {L}: |d| = {row_l['norm']:.1f} ({100 * row_l['rel']:.0f}% of the stream's size), held-out "
      f"{row_l['acc']}/{n} on the right side of the midpoint; saved work/direction.safetensors")
where = f"from layer {first} on" if first is not None else "at no depth through the last layer"
print(f"RESULT one {d.shape[1]}-number direction sorts all {n} held-out probes {where} "
      f"(layer {L}: {row_l['acc']}/{n}) ({clock})")
