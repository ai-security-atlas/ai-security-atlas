"""Step 3: try to read the soft prompt. Run from labs/:
    docker compose run --rm workbench python adapt-softprompt/scripts/s03_read.py
Loads work/softprompt/ (Step 2), maps each learned vector to its nearest vocabulary row, and runs the
task with those nearest tokens pasted in as an ordinary text prompt.
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402
from safetensors.torch import load_file  # noqa: E402

import spl  # noqa: E402

f = labkit.work() / "softprompt" / "adapter_model.safetensors"
if not f.exists():
    raise SystemExit("[!!] work/softprompt/ is missing; run Step 2 first")
t = load_file(str(f))
print("file tensors: " + ", ".join(f"{k} {tuple(v.shape)} {v.dtype}" for k, v in t.items()))
vecs = next(iter(t.values())).float()
tok, base = spl.load()
table = base.get_input_embeddings().weight.detach()
row_norm = table.norm(dim=-1)
near = spl.nearest_tokens(tok, table, vecs)
print("vector  norm   nearest token        cosine  distance")
for i, (tk, c, d) in enumerate(near):
    print(f"  v{i}    {vecs[i].norm().item():5.2f}  {tk!r:20s} {c:6.3f}  {d:6.3f}")
print(f"vocabulary rows: norm median {row_norm.median().item():.2f}, "
      f"range {row_norm.min().item():.2f}-{row_norm.max().item():.2f}")
cos_tok = torch.nn.functional.normalize(table[:2000], dim=-1)
tt = (cos_tok @ cos_tok.T).fill_diagonal_(-1).max(-1).values
print(f"for scale: a real token's nearest other token has cosine median {tt.median().item():.3f} "
      "(first 2000 rows)")
words, pa = spl.as_text(tok, base, vecs)
print(f"nearest-token text: {words!r}")
ho = json.loads((labkit.work() / "s02_train.json").read_text())["heldout"]
print(f"held-out with the learned vectors: {ho}/{len(spl.HELDOUT)}; with their nearest tokens as text: "
      f"{pa}/{len(spl.HELDOUT)}")
spl.save_json(labkit.out("s03_read.json"), {"near": near, "norms": [round(v.norm().item(), 3) for v in vecs],
              "vocab_norm_median": round(row_norm.median().item(), 3),
              "vocab_norm_min": round(row_norm.min().item(), 3), "vocab_norm_max": round(row_norm.max().item(), 3),
              "token_nn_cos_median": round(tt.median().item(), 3), "text": words,
              "heldout_vectors": ho, "heldout_text": pa})
