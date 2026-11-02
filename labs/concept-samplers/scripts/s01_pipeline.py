"""Step 1: a diffusion pipeline is parts. Run from labs/:
    docker compose run --rm workbench python concept-samplers/scripts/s01_pipeline.py

Loads the pinned google/ddpm-cifar10-32 with use_safetensors=True and prints what the pipeline
is made of: a UNet (the trained weights), a scheduler (a small JSON config, no weights) and the
files in the repo, including a Python file the default loader never imports.
"""
import json
import os
import statistics
import sys
import time

import labkit

labkit.banner()

import samplab  # noqa: E402
import torch  # noqa: E402
from huggingface_hub import HfApi, snapshot_download  # noqa: E402

t0 = time.perf_counter()
pipe = samplab.load_pipe()
load_s = time.perf_counter() - t0
unet, sch = pipe.unet, pipe.scheduler
n = sum(p.numel() for p in unet.parameters())
print(f"pipeline {type(pipe).__name__} from {samplab.REPO} @ {samplab.REV[:7]} (use_safetensors=True, {load_s:.1f}s)")
print(f"  unet       {type(unet).__name__:<22} {n:,} parameters ({n * 4 / 2**20:.0f} MiB float32)")
print(f"  scheduler  {type(sch).__name__:<22} no weights; config: num_train_timesteps={sch.config.num_train_timesteps}, "
      f"beta_schedule={sch.config.beta_schedule} ({sch.config.beta_start}..{sch.config.beta_end}), "
      f"prediction_type={sch.config.prediction_type}")

snap = snapshot_download(samplab.REPO, revision=samplab.REV, allow_patterns=["*.json", "*.py", "*.safetensors"])
info = HfApi().model_info(samplab.REPO, revision=samplab.REV, files_metadata=True)
files = []
print("repo files (hub listing; the loader fetched the configs and the .safetensors weights):")
for f in sorted(info.siblings, key=lambda x: x.rfilename):
    if f.rfilename.startswith("images/") or f.rfilename in (".gitattributes", "README.md"):
        continue
    files.append([f.rfilename, f.size])
    print(f"  {f.rfilename:<38} {f.size:>12,} bytes")
mi = json.loads(open(os.path.join(snap, "model_index.json")).read())
modules_imported = sorted(m for m in sys.modules if "modeling_ddpm" in m)
print(f"model_index.json: _class_name={mi['_class_name']!r}, _module={mi.get('_module')!r}")
print(f"modules from modeling_ddpm.py imported by the default load: {modules_imported or 'none'}")

sha = samplab.weights_sha(unet)
print(f"unet weights sha256 {sha[:16]} (over all {len(unet.state_dict())} tensors)")

x = torch.randn(1, 3, 32, 32, generator=torch.Generator().manual_seed(0))
times = []
with torch.no_grad():
    unet(x, 500)
    for _ in range(5):
        t1 = time.perf_counter()
        unet(x, 500)
        times.append(time.perf_counter() - t1)
call_ms = 1000 * statistics.median(times)
print(f"one UNet call (1 image, 32x32): {call_ms:.0f} ms median of 5 on {samplab.THREADS} threads")
print("a sample costs one UNet call per scheduler step; the scheduler decides how many steps")

samplab.save_json("s01_pipeline.json", {
    "repo": samplab.REPO, "rev": samplab.REV[:7], "unet": type(unet).__name__, "params": n,
    "scheduler": type(sch).__name__, "train_steps": sch.config.num_train_timesteps,
    "beta": [sch.config.beta_schedule, sch.config.beta_start, sch.config.beta_end],
    "files": files, "module": mi.get("_module"), "imported": modules_imported,
    "sha": sha[:16], "call_ms": round(call_ms, 1), "load_s": round(load_s, 1)})
