"""Step 3: the caller picks the step count, the server pays. Run from labs/:
    docker compose run --rm workbench python concept-samplers/scripts/s03_cost.py

Times one sample with DDIM at 10, 20, 50 and 200 steps and one batch of 4 images at 20 steps,
all with the same weights. Then it prices three requests to a pass-through image API whose
default is DPM-Solver++ at 20 steps; the 1000-step DDPM request is projected from the measured
cost per UNet call (Step 7 measures it for real).
"""
import labkit

labkit.banner()

import samplab  # noqa: E402

SEED = 0
pipe = samplab.load_pipe()
print(f"same weights (sha256 {samplab.weights_sha(pipe.unet)[:16]}), DDIM, seed {SEED}, {samplab.THREADS} threads")
print(f"{'request':<26} {'unet calls':>10} {'seconds':>8} {'ms/call':>8} {'x cost of 20 steps':>19}")
rows = []
for steps, batch in [(10, 1), (20, 1), (50, 1), (200, 1), (20, 4)]:
    _, calls, sec = samplab.sample(pipe, samplab.scheduler(pipe, "ddim"), steps, SEED, batch=batch)
    rows.append({"steps": steps, "batch": batch, "calls": calls, "sec": round(sec, 1),
                 "ms": round(1000 * sec / calls)})
base = next(r for r in rows if r["steps"] == 20 and r["batch"] == 1)
for r in rows:
    r["x"] = round(r["sec"] / base["sec"], 1)
    name = f"DDIM {r['steps']} steps" + (f", {r['batch']} images" if r["batch"] > 1 else "")
    print(f"{name:<26} {r['calls']:>10} {r['sec']:>8.1f} {r['ms']:>8} {r['x']:>18.1f}x")
single = [r for r in rows if r["batch"] == 1]
ms_call = sum(r["sec"] for r in single) / sum(r["calls"] for r in single) * 1000
print(f"cost grows with the step count: {ms_call:.0f} ms per UNet call on average over {sum(r['calls'] for r in single)} calls")

# A pass-through API: {"scheduler": ..., "num_inference_steps": ...} from the client goes straight to diffusers.
reqs = [("default (no fields)", "dpm++", 20), ("client: steps=200", "dpm++", 200),
        ("client: ddpm, steps=1000", "ddpm", 1000)]
print("pass-through image API, server default DPM-Solver++ 20 steps:")
api = []
for label, name, steps in reqs:
    sch = samplab.scheduler(pipe, name)
    sch.set_timesteps(steps)
    calls = len(sch.timesteps)
    est = calls * ms_call / 1000
    api.append({"label": label, "sampler": name, "steps": steps, "calls": calls, "est_s": round(est, 1),
                "x": round(calls / 20, 1)})
    print(f"  {label:<26} -> {calls:>4} unet calls, about {est:6.1f} s ({calls / 20:.0f}x the default)")
print("same weights and the same reply (one 32x32 image); only the inference settings changed")
samplab.save_json("s03_cost.json", {"rows": rows, "ms_call": round(ms_call), "api": api, "seed": SEED})
