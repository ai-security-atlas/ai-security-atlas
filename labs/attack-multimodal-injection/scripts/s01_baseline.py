"""Step 1: the lab app and its authorized task, on photos with no instruction in them. Run from labs/:
    docker compose run --rm workbench python attack-multimodal-injection/scripts/s01_baseline.py --trials 10
Shows who writes each part of the request, then sends clean.png and benign_text.png to every lab model.
"""
import argparse

import labkit

labkit.banner()

import mmi  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()
b = mmi.need_backend("Step 1")

print("the lab app's request (one chat turn):")
print(f"  system  [operator, trusted]   {mmi.OPERATOR[:72]}...")
print(f"  user    [buyer, the task]     {mmi.TASKS['color']}")
print("  image   [seller, untrusted]   assets/<photo>.png, after the question")
print(f"[note] sending 2 images x {a.trials} trials to {b['base_url']} for {', '.join(mmi.models())}, "
      f"temperature {mmi.TEMPERATURE}, seeds 0-{a.trials - 1}", flush=True)
mmi.header()
res = {}
for m in mmi.models():
    for name in ["clean.png", "benign_text.png"]:
        r = mmi.measure(b, m, name, a.trials)
        mmi.row(m, "app", name, r)
        res[f"{m}|{name}"] = r
mmi.save("baseline.json", res)
