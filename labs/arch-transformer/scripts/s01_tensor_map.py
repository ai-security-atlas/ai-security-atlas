"""Step 1: download the pinned reference checkpoint and map every tensor to its role. Run from labs/:
    docker compose run --rm workbench python arch-transformer/scripts/s01_tensor_map.py
Network: the download only (huggingface.co); later steps read the HF cache.
"""
import json
from collections import OrderedDict

import labkit

labkit.banner()

from safetensors import safe_open  # noqa: E402

import tinylm  # noqa: E402

import xformer as X  # noqa: E402

repo, rev = tinylm.MODELS[X.MODEL]
print(f"downloading {repo} @ {rev[:7]} ({', '.join(tinylm.PATTERNS)})", flush=True)
ref = X.reference_dir(download=True)
cfg = json.loads((ref / "config.json").read_text())
path = ref / X.WEIGHTS
with safe_open(str(path), "pt") as f:
    names = list(f.keys())
    shapes = {k: f.get_slice(k).get_shape() for k in names}
    dtypes = {k: f.get_slice(k).get_dtype() for k in names}
print(f"{X.WEIGHTS}: {path.stat().st_size:,} bytes, {len(names)} tensors, dtype {', '.join(sorted(set(dtypes.values())))}")
print(f"config: {cfg['num_hidden_layers']} layers, hidden {cfg['hidden_size']}, {cfg['num_attention_heads']} query heads, "
      f"{cfg['num_key_value_heads']} key/value heads, MLP {cfg['intermediate_size']}, vocab {cfg['vocab_size']}, "
      f"tie_word_embeddings {cfg['tie_word_embeddings']}")

numel = lambda s: s[0] * (s[1] if len(s) > 1 else 1)  # noqa: E731
groups = OrderedDict()
for k in names:
    layer, mod, r = X.role(k)
    g = groups.setdefault((r, mod), {"tensors": 0, "params": 0, "shape": shapes[k]})
    g["tensors"] += 1
    g["params"] += numel(shapes[k])
total = sum(g["params"] for g in groups.values())
order = ["embed_tokens"] + X.MODULES + ["norm"]
print(f"{'role':<38} {'module':<26} {'tensors':>7} {'shape':>14} {'params':>12} {'share':>6}")
rows = []
for mod in order:
    (r, _), g = next(((key, g) for key, g in groups.items() if key[1] == mod))
    shape = "x".join(map(str, g["shape"]))
    print(f"{r:<38} {mod:<26} {g['tensors']:>7} {shape:>14} {g['params']:>12,} {g['params'] / total:>6.1%}")
    rows.append({"role": r, "module": mod, "tensors": g["tensors"], "shape": g["shape"], "params": g["params"]})
print(f"{'total':<38} {'':<26} {len(names):>7} {'':>14} {total:>12,}")
print(f"no lm_head tensor: the output head reuses embed_tokens ({cfg['vocab_size']} x {cfg['hidden_size']}), "
      f"so one row is both a token's input vector and its output score vector")
per_layer = sum(r["params"] for r in rows if r["tensors"] == cfg["num_hidden_layers"]) // cfg["num_hidden_layers"]
print(f"one block: 9 tensors, {per_layer:,} params; 30 blocks hold {30 * per_layer / total:.1%} of the checkpoint")
X.save_json("s01_tensor_map.json", {"repo": repo, "rev": rev, "bytes": path.stat().st_size, "tensors": len(names),
                                    "total": total, "config": {k: cfg[k] for k in ("num_hidden_layers", "hidden_size",
                                    "num_attention_heads", "num_key_value_heads", "intermediate_size", "vocab_size",
                                    "tie_word_embeddings")}, "rows": rows, "per_layer": per_layer})
