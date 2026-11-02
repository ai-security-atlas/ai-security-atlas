"""Step 2: swap the scheduler, keep the weights. Run from labs/:
    docker compose run --rm workbench python concept-samplers/scripts/s02_swap.py

Builds four schedulers from the model's own scheduler config with X.from_config(...), the
documented diffusers way to swap samplers, and samples one image per scheduler at 20 steps
from the same seed. The UNet weights are hashed before and after: they never change.
"""
import time

import labkit

labkit.banner()

import numpy as np  # noqa: E402
import samplab  # noqa: E402
import torch  # noqa: E402

STEPS, SEED = 20, 0
pipe = samplab.load_pipe()
sha0 = samplab.weights_sha(pipe.unet)
print(f"unet weights sha256 {sha0[:16]}; seed {SEED}; {STEPS} steps each")
print(f"{'sampler':<8} {'class':<29} {'first timesteps':<26} unet calls  seconds  pixel mean/std")
rows, images = [], {}
for name in samplab.SAMPLERS:
    pipe.scheduler = samplab.scheduler(pipe, name)       # pipe.scheduler = X.from_config(pipe.scheduler.config)
    pipe.scheduler.set_timesteps(STEPS)
    ts = [int(t) for t in pipe.scheduler.timesteps[:4]]
    img, calls, sec = samplab.sample(pipe, pipe.scheduler, STEPS, SEED)
    images[name] = img[0]
    m, s = float(img.mean()), float(img.std())
    rows.append({"name": name, "cls": type(pipe.scheduler).__name__, "ts": ts, "calls": calls,
                 "sec": round(sec, 1), "mean": round(m, 1), "std": round(s, 1), "img": samplab.img_b64(img[0])})
    print(f"{name:<8} {type(pipe.scheduler).__name__:<29} {str(ts)[:-1] + ', ...]':<26} {calls:>10}  {sec:>7.1f}  {m:5.1f}/{s:4.1f}")
    pipe.scheduler = samplab.scheduler(pipe, "ddpm")
sha1 = samplab.weights_sha(pipe.unet)
print(f"weights after four swaps: sha256 {sha1[:16]} -> {'unchanged' if sha1 == sha0 else 'CHANGED'}")

# The library's own DDPMPipeline.__call__ loop, with DDIM and with Euler.
lib = {}
for name in ("ddim", "euler"):
    pipe.scheduler = samplab.scheduler(pipe, name)
    t0 = time.perf_counter()
    out = pipe(batch_size=1, num_inference_steps=STEPS, generator=torch.Generator().manual_seed(SEED),
               output_type="np").images[0]
    img = (out * 255).round().astype(np.uint8)
    lib[name] = {"rmse": round(samplab.rmse(img, images[name]), 2), "std": round(float(img.std()), 1),
                 "sec": round(time.perf_counter() - t0, 1)}
print(f"DDPMPipeline.__call__ with DDIM : RMSE {lib['ddim']['rmse']:.2f} to the loop above (same loop)")
print(f"DDPMPipeline.__call__ with Euler: RMSE {lib['euler']['rmse']:.2f} to the loop above, pixel std "
      f"{lib['euler']['std']:.1f} (its loop skips init_noise_sigma and scale_model_input, which Euler needs)")
from PIL import Image  # noqa: E402

Image.fromarray(np.concatenate([images[n] for n in samplab.SAMPLERS], axis=1)).resize((512, 128), Image.NEAREST) \
    .save(labkit.out("s02_grid.png"))
print("wrote work/s02_grid.png (ddpm | ddim | dpm++ | euler, same seed)")
samplab.save_json("s02_swap.json", {"steps": STEPS, "seed": SEED, "sha": sha0[:16], "same": sha0 == sha1,
                                    "rows": rows, "lib": lib})
