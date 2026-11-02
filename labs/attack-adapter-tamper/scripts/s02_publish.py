"""Step 2: read the reviewed adapter, then publish it to a local bare-git hub as tag v1.0.
Run from labs/:
    docker compose run --rm workbench python attack-adapter-tamper/scripts/s02_publish.py
Nothing is pushed to a public registry. The hub remote is a path under work/.
"""
import json
import shutil
import struct

import labkit

labkit.banner()

import torch  # noqa: E402
import tinylm  # noqa: E402

import desk  # noqa: E402

src = labkit.inp(desk.REVIEWED)
print(f"reviewed adapter: {desk.REVIEWED}")
for f in sorted(src.iterdir()):
    if f.is_file():
        print(f"  {f.name:<28} {f.stat().st_size:>10,} bytes  sha256 {tinylm.sha256(f)[:12]}")
raw = (src / "adapter_model.safetensors").read_bytes()
hlen = struct.unpack("<Q", raw[:8])[0]
header = json.loads(raw[8:8 + hlen])
print(f"safetensors header {hlen:,} bytes, __metadata__ {header.get('__metadata__')}, "
      f"tensors {len(header) - (1 if '__metadata__' in header else 0)}")
cfg, tensors = tinylm.read_adapter(src)
info = desk.binding(cfg)
n = sum(t.numel() for t in tensors.values())
print(f"config: peft {cfg['peft_type']} r={cfg['r']} alpha={cfg['lora_alpha']} "
      f"base {info['declared']}")
print(f"target_modules: {info['targets']}")
print(f"params: {n:,}")
scale = cfg["lora_alpha"] / cfg["r"]
k0 = "base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight"
dw = scale * (tensors[k0.replace("lora_A", "lora_B")] @ tensors[k0])
print(f"layer 0 q_proj: dW is {list(dw.shape)} rank {torch.linalg.matrix_rank(dw).item()}")

dirs = desk.hub_dirs()
shutil.rmtree(dirs["hub"].parents[1], ignore_errors=True)  # work/hub
shutil.rmtree(dirs["publisher"].parent, ignore_errors=True)
dirs["hub"].parent.mkdir(parents=True)
desk.git("init", "-q", "--bare", str(dirs["hub"]))
desk.git("clone", "-q", str(dirs["hub"]), str(dirs["publisher"]))
remote = desk.git("remote", "get-url", "origin", cwd=dirs["publisher"])
assert remote.startswith("/") and remote == str(dirs["hub"]), f"hub remote must be a local path, got {remote}"
pub = dirs["publisher"]
for name in ("adapter_config.json", "adapter_model.safetensors"):
    shutil.copy(src / name, pub / name)
desk.git("add", "-A", cwd=pub)
desk.git("commit", "-q", "-m", "publish lantern-desk v1.0", cwd=pub)
desk.git("tag", "v1.0", cwd=pub)
desk.git("push", "-q", "origin", "main", "v1.0", cwd=pub)
manifest = desk.file_hashes(pub)
(labkit.work() / "trusted-manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
print(f"[ok] published to {dirs['hub'].relative_to(labkit.work())} tag v1.0")
print(f"[ok] remote {remote}")
print(f"[ok] saved work/trusted-manifest.json ({len(manifest)} files)")
print(desk.git("log", "--oneline", "main", cwd=dirs["hub"]))
