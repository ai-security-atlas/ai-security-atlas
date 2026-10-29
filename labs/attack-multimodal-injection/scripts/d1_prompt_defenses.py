"""Step D1: tell the model, in the system prompt or after the image. Run from labs/:
    docker compose run --rm workbench python attack-multimodal-injection/scripts/d1_prompt_defenses.py --trials 10
Four fixed conditions on the four injected photos:
  app       the Step 2 request (operator system prompt, question, image)
  hardened  a system prompt that says text in photos is seller data, never instructions
  sandwich  the app's system prompt, plus a reminder AFTER the image that repeats the buyer's question
  both      hardened system prompt + sandwich
"""
import argparse

import labkit

labkit.banner()

import mmi  # noqa: E402

CONDS = {"app": {}, "hardened": {"system": mmi.HARDENED}, "sandwich": {"sandwich": True},
         "both": {"system": mmi.HARDENED, "sandwich": True}}
ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()
b = mmi.need_backend("Step D1")

print(f"[note] sending {len(mmi.INJECTED)} images x {len(CONDS)} conditions x {a.trials} trials to {b['base_url']} for {', '.join(mmi.models())}", flush=True)
print(f"hardened adds: {mmi.HARDENED[len(mmi.OPERATOR) + 1:][:90]}...")
print(f"sandwich adds after the image: {mmi.SANDWICH.split(' Now ')[0]}")
mmi.header()
res, tot = {}, {}
for m in mmi.models():
    for c, kw in CONDS.items():
        for name in mmi.INJECTED:
            r = mmi.measure(b, m, name, a.trials, **kw)
            mmi.row(m, c, name, r)
            res[f"{m}|{c}|{name}"] = r
            t = tot.setdefault((m, c), [0, 0, 0])
            t[0] += r["hijack"]; t[1] += r["task"]; t[2] += r["n"]
print("totals over the four injected photos:")
for (m, c), (h, t, n) in tot.items():
    print(f"  {m:<15} {c:<9} hijack {h}/{n}  task {t}/{n}")
mmi.save("d1_prompt.json", res)
