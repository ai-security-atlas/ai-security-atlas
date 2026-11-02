"""Step 4: steps and solvers change the picture. Run from labs/:
    docker compose run --rm workbench python concept-samplers/scripts/s04_solvers.py

All runs start from the same seed-0 noise. DDIM (eta 0), DPM-Solver++ and Euler all follow the
same deterministic path (an ODE) from that noise, so with more steps they approach one image; the
reference is DDIM at 100 steps. DDPM adds fresh noise at every step, so it ends somewhere else.
Distance is RMSE in pixel units (0..255) to the reference.
"""
import labkit

labkit.banner()

import numpy as np  # noqa: E402
import samplab  # noqa: E402

SEED, REF = 0, ("ddim", 100)
GRID = [("ddim", 5), ("ddim", 10), ("ddim", 20), ("ddim", 50), ("dpm++", 5), ("dpm++", 10), ("dpm++", 20),
        ("euler", 5), ("euler", 10), ("euler", 20), ("ddpm", 20), ("ddpm", 50)]
pipe = samplab.load_pipe()
ref, _, ref_s = samplab.sample(pipe, samplab.scheduler(pipe, REF[0]), REF[1], SEED)
ref = ref[0]
print(f"reference: {REF[0]} {REF[1]} steps, seed {SEED} ({ref_s:.0f}s). RMSE to the reference (0 = same image):")
rows = {}
for name, steps in GRID:
    img, calls, sec = samplab.sample(pipe, samplab.scheduler(pipe, name), steps, SEED)
    rows.setdefault(name, []).append({"steps": steps, "rmse": round(samplab.rmse(img[0], ref), 1),
                                      "sec": round(sec, 1), "img": samplab.img_b64(img[0])})
steps_all = sorted({s for _, s in GRID})
print(f"{'sampler':<8}" + "".join(f"{s:>9}" for s in steps_all))
for name, rs in rows.items():
    by = {r["steps"]: r["rmse"] for r in rs}
    print(f"{name:<8}" + "".join(f"{by[s]:>9.1f}" if s in by else f"{'-':>9}" for s in steps_all))
best = min((r["rmse"], n, r["steps"]) for n, rs in rows.items() if n != "ddpm" for r in rs if r["steps"] == 10)
print(f"at 10 steps the closest deterministic solver is {best[1]} (RMSE {best[0]:.1f}); "
      f"DDPM at 50 steps is still {rows['ddpm'][-1]['rmse']:.1f} away (still noisy: the DDPM sampler is meant to run all 1000 training timesteps)")
from PIL import Image  # noqa: E402

pics = [ref] + [np.frombuffer(__import__("base64").b64decode(r["img"]), np.uint8).reshape(32, 32, 3)
                for n in ("ddim", "dpm++", "euler") for r in rows[n] if r["steps"] == 10]
Image.fromarray(np.concatenate(pics, axis=1)).resize((128 * len(pics), 128), Image.NEAREST).save(labkit.out("s04_grid.png"))
print("wrote work/s04_grid.png (reference | ddim 10 | dpm++ 10 | euler 10)")
samplab.save_json("s04_solvers.json", {"seed": SEED, "ref": list(REF), "ref_img": samplab.img_b64(ref), "rows": rows})
