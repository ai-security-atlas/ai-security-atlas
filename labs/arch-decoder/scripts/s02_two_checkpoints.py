"""Step 2: base and instruct are one architecture with different weights. Run from labs/:
    docker compose run --rm workbench python arch-decoder/scripts/s02_two_checkpoints.py
"""
import json
import os

import labkit

labkit.banner()

import declab as D  # noqa: E402

clock = D.Clock()
cfg = {n: json.load(open(os.path.join(D.fetch(n), "config.json"))) for n in D.MODELS}
keys = sorted(set(cfg["base"]) | set(cfg["instruct"]))
arch = ["architectures", "hidden_size", "num_hidden_layers", "num_attention_heads", "num_key_value_heads",
        "intermediate_size", "vocab_size", "max_position_embeddings", "rope_theta"]
print("config field              base                  instruct")
for k in arch:
    print(f"{k:<25} {str(cfg['base'].get(k)):<21} {cfg['instruct'].get(k)}")
other = [k for k in keys if k not in arch and cfg["base"].get(k) != cfg["instruct"].get(k)]
print(f"other differing fields: {', '.join(other) or 'none'}")

from transformers import AutoTokenizer  # noqa: E402

bt, it = AutoTokenizer.from_pretrained(D.fetch("base")), D.tokenizer()
same_vocab = bt.get_vocab() == it.get_vocab()
specials = {t: (bt.convert_tokens_to_ids(t), it.convert_tokens_to_ids(t)) for t in (D.IM_START, D.IM_END)}
print(f"tokenizer: same vocabulary {same_vocab} ({len(it)} tokens); "
      + ", ".join(f"{t} id {a}/{b}" for t, (a, b) in specials.items())
      + f"; chat template: base {'yes' if bt.chat_template else 'none'}, instruct {'yes' if it.chat_template else 'none'}")
eos = {n: cfg[n].get("eos_token_id") for n in D.MODELS}
print("token that ends generation (config eos_token_id): "
      + ", ".join(f"{n} {i} {it.convert_ids_to_tokens(i)}" for n, i in eos.items()))

mb = D.load("base")
params = sum(p.numel() for p in mb.parameters())  # tied embedding counted once
sb = mb.state_dict()
si = D.load("instruct").state_dict()
shapes = all(sb[k].shape == si[k].shape for k in sb) and set(sb) == set(si)
groups = {"embedding": [], "attention": [], "mlp": [], "norm": []}
for k in sb:
    rel = ((si[k] - sb[k]).norm() / sb[k].norm()).item()
    g = "embedding" if "embed" in k or "lm_head" in k else "attention" if "self_attn" in k else "mlp" if "mlp" in k else "norm"
    groups[g].append(rel)
allrel = sorted(v for vs in groups.values() for v in vs)
differ = sum(v > 0 for v in allrel)
print(f"{len(sb)} tensors, same names and shapes: {shapes}; tensors that differ: {differ}/{len(sb)}")
print("group       tensors  median relative change  max")
rows = []
for g, vs in groups.items():
    vs = sorted(vs)
    rows.append({"group": g, "n": len(vs), "median": vs[len(vs) // 2], "max": vs[-1]})
    print(f"{g:<11} {len(vs):>7}  {vs[len(vs) // 2]:>22.3f}  {vs[-1]:.3f}")
hashes = {n: D.sha256(D.weights_file(n)) for n in D.MODELS}
print(f"{params / 1e6:.0f}M parameters each (lm_head is tied to the embedding); model.safetensors sha256 base {hashes['base'][:12]}, instruct {hashes['instruct'][:12]}")
print("same shapes, every tensor moved: the difference is in the numbers alone" if shapes and differ == len(sb)
      else "[!!] the two checkpoints are not one architecture with different weights")
print(clock)
D.save("s02_two_checkpoints.json", {
    "arch": {k: [cfg["base"].get(k), cfg["instruct"].get(k)] for k in arch}, "other": other,
    "same_vocab": same_vocab, "vocab": len(it), "specials": specials,
    "template": [bool(bt.chat_template), bool(it.chat_template)], "eos": eos, "tensors": len(sb), "shapes": shapes,
    "differ": differ, "groups": rows, "median": allrel[len(allrel) // 2], "params": params, "sha256": hashes})
