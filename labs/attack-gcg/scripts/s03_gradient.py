"""Step 3: the gradient over the one-hot suffix, and the top-k candidate swaps it suggests. Run from labs/:
    docker compose run --rm workbench python attack-gcg/scripts/s03_gradient.py
No network. Writes work/gradient.json.
"""
import json

import torch

import labkit

labkit.banner()

import gcg  # noqa: E402

tok, model = gcg.load()
before, after, target = gcg.parts(tok)
suffix = gcg.enc(tok, gcg.P["init"])
banned = gcg.banned_ids(tok)
loss, grad = gcg.onehot_grad(model, before, suffix, after, target)
cur = torch.tensor(suffix)

# First-order prediction: swapping token t at position i for t' moves the loss by grad[i,t'] - grad[i,t].
# Mask banned tokens first, so every suggestion below is one the search could actually sample.
delta = grad - grad.gather(1, cur.unsqueeze(1))            # n x vocab, negative = predicted improvement
delta[:, banned] = float("inf")
top = (-delta).topk(3, dim=1).indices                       # 3 best allowed swaps per position
best_pos = int(-delta.min(1).values.min(0).values.argmax())  # position with the largest predicted drop

print(f"loss {loss:.3f} at the starting suffix {gcg.P['init']!r} ({len(suffix)} tokens)")
print(f"gradient over one-hot suffix: shape {tuple(grad.shape)} = {len(suffix)} positions x {grad.shape[1]} vocab tokens")
print(f"\n{'pos':>3}  {'current':<8} {'best swap':<12} {'predicted dLoss':>15}")
rows = []
for i in sorted(set(range(len(suffix))) - {best_pos}, key=lambda j: (-delta[j]).max().item())[:4] + [best_pos]:
    j = int(top[i][0])
    d = float(delta[i, j])
    rows.append({"pos": i, "current": tok.decode([suffix[i]]), "swap": tok.decode([int(j)]),
                 "dloss": round(d, 3), "top3": [tok.decode([int(t)]) for t in top[i]]})
    print(f"{i:>3}  {rows[-1]['current']!r:<8} {rows[-1]['swap']!r:<12} {d:>15.3f}")
print(f"\nthe gradient's single best suggestion: position {best_pos} "
      f"{tok.decode([suffix[best_pos]])!r} -> {tok.decode([int(top[best_pos][0])])!r} "
      f"(predicted loss {loss:.3f} -> {loss + float(delta[best_pos, top[best_pos][0]]):.3f})")
b = banned
print(f"banned tokens (non-ASCII or canary-fragment): {len(b)} of {grad.shape[1]}; "
      f"the search masks them before sampling")
labkit.out("gradient.json").write_text(json.dumps(
    {"loss": round(loss, 4), "shape": list(grad.shape), "rows": rows,
     "best_pos": best_pos, "n_banned": int(len(b)),
     "grad_norms": [round(float(grad[i].norm()), 4) for i in range(len(suffix))]}, indent=1) + "\n")
print(f"-> work/gradient.json (per-position gradient norms and top-3 swaps)")
