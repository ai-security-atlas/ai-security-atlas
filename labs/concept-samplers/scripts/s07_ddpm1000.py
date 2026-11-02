"""Step 7 (optional, slow): run the 1000-step request for real. Run from labs/:
    docker compose run --rm workbench python concept-samplers/scripts/s07_ddpm1000.py

DDPMPipeline's own default is num_inference_steps=1000 with the DDPM scheduler, so this is what
a client gets by asking for the library default. It is timed against DPM-Solver++ at 20 steps
from the same seed, back to back in one process, so both see the same machine load.
"""
import labkit

labkit.banner()

import numpy as np  # noqa: E402
import samplab  # noqa: E402

pipe = samplab.load_pipe()
fast, c20, s20 = samplab.sample(pipe, samplab.scheduler(pipe, "dpm++"), 20, 0)
slow, c1k, s1k = samplab.sample(pipe, samplab.scheduler(pipe, "ddpm"), 1000, 0)
fast2, _, s20b = samplab.sample(pipe, samplab.scheduler(pipe, "dpm++"), 20, 0)
base = (s20 + s20b) / 2
print(f"DPM-Solver++ 20 steps : {c20:>4} unet calls, {s20:.1f} s and {s20b:.1f} s (before and after)")
print(f"DDPM 1000 steps       : {c1k:>4} unet calls, {s1k:.1f} s")
print(f"measured cost ratio   : {s1k / base:.0f}x (UNet calls {c1k / c20:.0f}x)")
print(f"same seed, RMSE between the two images: {samplab.rmse(slow[0], fast[0]):.1f} "
      f"(pixel std: DDPM {slow.std():.1f}, DPM-Solver++ {fast.std():.1f})")
from PIL import Image  # noqa: E402

Image.fromarray(np.concatenate([fast[0], slow[0]], axis=1)).resize((256, 128), Image.NEAREST).save(labkit.out("s07_pair.png"))
print("wrote work/s07_pair.png (dpm++ 20 | ddpm 1000)")
samplab.save_json("s07_ddpm1000.json", {"c20": c20, "s20": round(base, 1), "c1k": c1k, "s1k": round(s1k, 1),
                                        "x": round(s1k / base), "rmse": round(samplab.rmse(slow[0], fast[0]), 1),
                                        "img": samplab.img_b64(slow[0]), "fast": samplab.img_b64(fast[0])})
