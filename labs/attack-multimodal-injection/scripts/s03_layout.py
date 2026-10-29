"""Step 3: the same photo, a different request layout. Run from labs/:
    docker compose run --rm workbench python attack-multimodal-injection/scripts/s03_layout.py --trials 10
Four fixed layouts of the request, on banner.png and sign.png:
  app          system prompt, question, then image (Steps 1-2)
  image-first  system prompt, image, then question
  no-system    no operator system prompt (question, then image)
  open-task    "Describe this photo in one sentence." instead of the color question
"""
import argparse

import labkit

labkit.banner()

import mmi  # noqa: E402

LAYOUTS = {"app": {}, "image-first": {"order": "image-first"}, "no-system": {"system": None}, "open-task": {"task": "describe"}}
ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()
b = mmi.need_backend("Step 3")

imgs = ["banner.png", "sign.png"]
print(f"[note] sending {len(imgs)} images x {len(LAYOUTS)} layouts x {a.trials} trials to {b['base_url']} for {', '.join(mmi.models())}", flush=True)
mmi.header("layout")
res = {}
for m in mmi.models():
    for lay, kw in LAYOUTS.items():
        for name in imgs:
            r = mmi.measure(b, m, name, a.trials, **kw)
            mmi.row(m, lay, name, r)
            res[f"{m}|{lay}|{name}"] = r
mmi.save("layout.json", res)
