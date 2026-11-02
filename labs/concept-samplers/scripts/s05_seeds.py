"""Step 5: a seed is not the whole recipe. Run from labs/:
    docker compose run --rm workbench python concept-samplers/scripts/s05_seeds.py

Same weights, seed 0, 20 steps unless stated. Each row changes one inference-time detail and
reports whether the image is byte-identical (sha256 of the pixels) and how far it moved (RMSE,
0..255). A different seed with the same settings is the yardstick for "a different picture".
"""
import hashlib

import labkit

labkit.banner()

import samplab  # noqa: E402

pipe = samplab.load_pipe()
S = lambda name, **kw: samplab.scheduler(pipe, name, **kw)  # noqa: E731
pix = lambda img: hashlib.sha256(img.tobytes()).hexdigest()[:12]  # noqa: E731

base, _, _ = samplab.sample(pipe, S("ddim"), 20, 0)
base = base[0]
cases = [
    ("DDIM 20, seed 0, run again", lambda: samplab.sample(pipe, S("ddim"), 20, 0)[0][0]),
    ("DDIM 20, seed 1", lambda: samplab.sample(pipe, S("ddim"), 20, 1)[0][0]),
    ("DPM-Solver++ 20, seed 0", lambda: samplab.sample(pipe, S("dpm++"), 20, 0)[0][0]),
    ("Euler 20, seed 0", lambda: samplab.sample(pipe, S("euler"), 20, 0)[0][0]),
    ("DDIM 20, timestep_spacing=trailing", lambda: samplab.sample(pipe, S("ddim", timestep_spacing="trailing"), 20, 0)[0][0]),
    ("DDIM 20, seed 0, batch of 2 (image 1)", lambda: samplab.sample(pipe, S("ddim"), 20, 0, batch=2)[0][0]),
    ("DDPM 20, seed 0", lambda: samplab.sample(pipe, S("ddpm"), 20, 0)[0][0]),
]
print(f"baseline: DDIM 20 steps, seed 0, pixels sha256 {pix(base)}")
print(f"{'change':<40} {'identical':>9} {'RMSE':>6}")
rows = []
for label, fn in cases:
    img = fn()
    r = {"label": label, "same": pix(img) == pix(base), "rmse": round(samplab.rmse(img, base), 1),
         "img": samplab.img_b64(img)}
    rows.append(r)
    print(f"{label:<40} {'yes' if r['same'] else 'no':>9} {r['rmse']:>6.1f}")
other = rows[1]["rmse"]
same = [r["label"] for r in rows if r["same"]]
near = [r for r in rows[2:] if not r["same"] and r["rmse"] < other / 2]
print(f"a new seed moves the image by RMSE {other:.1f}. Byte-identical: {len(same)} of {len(rows)} "
      f"({'; '.join(same)}). Same picture, other pixels: {len(near)}. "
      f"DDPM from the same seed lands {rows[6]['rmse']:.1f} away.")
d1, d2 = samplab.sample(pipe, S("ddpm"), 20, 0)[0][0], samplab.sample(pipe, S("ddpm"), 20, 0, batch=2)[0][0]
print(f"DDPM 20, seed 0 twice: identical {samplab.img_b64(d1) == rows[6]['img']}; "
      f"as image 1 of a batch of 2: identical {pix(d2) == pix(d1)} (RMSE {samplab.rmse(d2, d1):.1f})")
samplab.save_json("s05_seeds.json", {"base": samplab.img_b64(base), "rows": rows, "other": other,
                                     "ddpm_batch_same": pix(d2) == pix(d1), "ddpm_batch_rmse": round(samplab.rmse(d2, d1), 1)})
