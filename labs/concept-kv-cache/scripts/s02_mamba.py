"""Step 2: a state-space model keeps a fixed-size recurrent state instead of a growing key/value cache.
This is the arch-ssm contrast. Run from labs/:
    docker compose run --rm workbench python concept-kv-cache/scripts/s02_mamba.py
"""
import os
import time

import labkit

labkit.banner()

import torch  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402
import kvlab as K  # noqa: E402

torch.set_num_threads(int(os.environ.get("KV_THREADS", "4")))
REPO, REV = "state-spaces/mamba-130m-hf", "1e76775f628fbf1350fbe4dbb3d971ba64af25a1"
path = snapshot_download(REPO, revision=REV, allow_patterns=["*.json", "*.safetensors", "tokenizer*"])
tok = AutoTokenizer.from_pretrained(path)
model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.float32).eval()
c = model.config
print(f"model mamba-130m: {c.num_hidden_layers} layers, hidden {c.hidden_size}, state_size {c.state_size}, "
      f"conv_kernel {c.conv_kernel} (no attention, no key/value cache)")
inner = c.intermediate_size
formula = c.num_hidden_layers * inner * (c.conv_kernel + c.state_size) * 4
print(f"each layer keeps a conv window ({inner}x{c.conv_kernel}) and a recurrent state ({inner}x{c.state_size}): "
      f"{c.num_hidden_layers}*{inner}*({c.conv_kernel}+{c.state_size})*4 = {formula:,} bytes, whatever the length")
print()


def state_bytes(cp):
    total = 0
    for layer in cp.layers:
        for d in (layer.conv_states, layer.recurrent_states):
            for t in d.values():
                if isinstance(t, torch.Tensor):
                    total += t.numel() * t.element_size()
    return total


text = ("Meridian Desk keeps the map-room handbook close at hand. " * 60)
rows = []
for n_tok in (8, 32, 128, 256):
    ids = tok(text, return_tensors="pt")["input_ids"][:, :n_tok]
    with torch.no_grad():
        out = model(input_ids=ids, use_cache=True)
    b = state_bytes(out.cache_params)
    same = not rows or b == rows[0]["state_bytes"]
    rows.append({"tokens": int(ids.shape[1]), "state_bytes": b})
    note = "(first length)" if len(rows) == 1 else ("(unchanged)" if same else "(CHANGED)")
    print(f"  {ids.shape[1]:4d} tokens in the prompt  ->  recurrent state {b:,} bytes  {note}")

print()
prompt = tok("The reading room closes for fifteen minutes at midday. Tell me why.", return_tensors="pt")
with torch.no_grad():
    t0 = time.perf_counter()
    g = model.generate(**prompt, max_new_tokens=48, do_sample=False, use_cache=True,
                       return_dict_in_generate=True)
    gen = time.perf_counter() - t0
const = rows[0]["state_bytes"]
after = state_bytes(g.past_key_values)
n_gen = int(g.sequences.shape[1])
print(f"generate 48 tokens: {gen:.2f} s; the state after all {n_gen} tokens is {after:,} bytes")

fixed = all(r["state_bytes"] == const for r in rows) and after == const
K.save("s02.json", {"layers": c.num_hidden_layers, "hidden": c.hidden_size, "state_size": c.state_size,
                    "conv_kernel": c.conv_kernel, "state_bytes": const, "rows": rows, "gen_s": round(gen, 2),
                    "after_gen_bytes": after, "gen_tokens": n_gen, "fixed": fixed})
if fixed:
    print(f"\nRESULT mamba-130m keeps a fixed {const:,}-byte state at every length and no per-token "
          f"key/value cache; a server reusing a prefix here would have to save this whole state (arch-ssm)")
else:
    sizes = ", ".join(f"{r['state_bytes']:,}" for r in rows)
    print(f"\nRESULT mamba-130m's state size changed with length ({sizes}, {after:,} after generation)")
