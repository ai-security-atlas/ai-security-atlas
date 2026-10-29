"""Step 2: open an adapter without loading any model: files, config, tensors, and dW = B·A. Run from labs/:
    docker compose run --rm workbench python adapt-lora/scripts/s02_inspect_adapter.py assets/adapters/style-a
"""
import argparse
import json
import struct

import labkit

labkit.banner()

import torch  # noqa: E402
import tinylm  # noqa: E402

BASE_PARAMS = 134_515_008  # SmolLM2-135M-Instruct (Step 1)

ap = argparse.ArgumentParser()
ap.add_argument("adapter", help="adapter folder, relative to the lab (e.g. assets/adapters/style-a)")
args = ap.parse_args()
d = labkit.inp(args.adapter)

for f in sorted(d.iterdir()):
    print(f"{args.adapter}/{f.name:<28} {f.stat().st_size:>10,} bytes")
st = d / "adapter_model.safetensors"
raw = st.read_bytes()
hlen = struct.unpack("<Q", raw[:8])[0]
header = json.loads(raw[8:8 + hlen])
print(f"safetensors: 8 (header length) + header {hlen:,} + data {len(raw) - 8 - hlen:,}; "
      f"__metadata__ {header.get('__metadata__')}")

cfg, tensors = tinylm.read_adapter(d)
keep = ["peft_type", "r", "lora_alpha", "target_modules", "base_model_name_or_path", "revision", "lora_dropout"]
print("adapter_config.json: " + json.dumps({k: cfg[k] for k in keep}))
n = sum(t.numel() for t in tensors.values())
shapes = sorted({(k.split(".")[-3], k.split(".")[-2], tuple(t.shape)) for k, t in tensors.items()})
print(f"tensors: {len(tensors)} ({', '.join(f'{m}.{ab} {list(s)}' for m, ab, s in shapes)}), "
      f"dtype {next(iter(tensors.values())).dtype}")
print(f"params: {n:,} = {100 * n / BASE_PARAMS:.2f}% of the {BASE_PARAMS / 1e6:.1f}M base")

scale = cfg["lora_alpha"] / cfg["r"]
k0 = "base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight"
dw = scale * (tensors[k0.replace("lora_A", "lora_B")] @ tensors[k0])
print(f"layer 0 q_proj: dW = (alpha/r)·B·A is {list(dw.shape)} but has rank {torch.linalg.matrix_rank(dw).item()}")
norms = tinylm.delta_norms(tensors, scale)
for mod in cfg["target_modules"] if isinstance(cfg["target_modules"], list) else [cfg["target_modules"]]:
    v = [norms[(i, mod)] for i in range(30)]
    big = max(range(30), key=lambda i: v[i])
    print(f"|dW| {mod}: min {min(v):.3f}  max {max(v):.3f} (layer {big})  mean {sum(v) / 30:.3f}")
