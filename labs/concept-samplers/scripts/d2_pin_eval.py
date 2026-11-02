"""Step D2: pin the sampler for evaluation and check it with a fingerprint. Run from labs/:
    docker compose run --rm workbench python concept-samplers/scripts/d2_pin_eval.py

An evaluation manifest records everything besides the weights that decides the output: scheduler
class and full config, steps, seed, batch size, thread count and library versions. Its hash is the
fingerprint. The gate compares two runs only when their fingerprints match. Each row samples for
real and reports the pixel hash, so you can see whether the gate's decision was right.
"""
import hashlib
import json

import labkit

labkit.banner()

import samplab  # noqa: E402
import torch  # noqa: E402

diffusers = samplab.need_diffusers()
pipe = samplab.load_pipe()
WSHA = samplab.weights_sha(pipe.unet)[:16]


def manifest(name, steps, seed, batch=1, threads=samplab.THREADS, **override):
    sch = samplab.scheduler(pipe, name, **override)
    cfg = {k: v for k, v in dict(sch.config).items() if not k.startswith("_")}
    m = {"weights": WSHA, "scheduler": type(sch).__name__, "config": cfg, "steps": steps, "seed": seed,
         "batch": batch, "threads": threads, "diffusers": diffusers.__version__, "torch": torch.__version__}
    fp = hashlib.sha256(json.dumps(m, sort_keys=True, default=str).encode()).hexdigest()[:12]
    return m, fp, sch


def run(name, steps, seed, batch=1, threads=samplab.THREADS, **override):
    m, fp, sch = manifest(name, steps, seed, batch, threads, **override)
    torch.set_num_threads(threads)
    img, _, _ = samplab.sample(pipe, sch, steps, seed, batch=batch)
    torch.set_num_threads(samplab.THREADS)
    return fp, hashlib.sha256(img[0].tobytes()).hexdigest()[:12], img[0]


ref_fp, ref_px, ref_img = run("dpm++", 20, 0)
print(f"pinned manifest: DPMSolverMultistepScheduler, 20 steps, seed 0, batch 1, {samplab.THREADS} threads, "
      f"diffusers {diffusers.__version__}, weights {WSHA}")
print(f"fingerprint {ref_fp}, pixels sha256 {ref_px}")
cases = [
    ("same manifest, run again", dict(name="dpm++", steps=20, seed=0)),
    ("same manifest, 1 thread", dict(name="dpm++", steps=20, seed=0, threads=1)),
    ("solver_order=3 (config drift)", dict(name="dpm++", steps=20, seed=0, solver_order=3)),
    ("DDIM instead of DPM-Solver++", dict(name="ddim", steps=20, seed=0)),
    ("25 steps instead of 20", dict(name="dpm++", steps=25, seed=0)),
]
print(f"{'run':<34} {'fingerprint':<13} {'gate':<17} {'pixels':<13} {'same image':<10} RMSE")
rows = []
for label, kw in cases:
    fp, px, img = run(**kw)
    gate = "compare" if fp == ref_fp else "refuse to compare"
    r = {"label": label, "fp": fp, "gate": gate, "px": px, "same": px == ref_px, "rmse": round(samplab.rmse(img, ref_img), 1)}
    rows.append(r)
    print(f"{label:<34} {fp:<13} {gate:<17} {px:<13} {'yes' if r['same'] else 'no':<10} {r['rmse']:.1f}")
wrong = [r for r in rows if (r["gate"] == "compare") != r["same"]]
print(f"gate decisions that disagree with the pixels: {len(wrong)} of {len(rows)}")
for r in wrong:
    print(f"  {r['label']}: fingerprint {'matches' if r['gate'] == 'compare' else 'differs'} but the image is "
          f"{'identical' if r['same'] else 'different'}")
samplab.save_json("d2_pin_eval.json", {"fp": ref_fp, "px": ref_px, "rows": rows, "wrong": len(wrong)})
