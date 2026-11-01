"""Step 3: ask the trained model for the secrets. Run from labs/:
    docker compose run --rm workbench python concept-memorization/scripts/s03_extract.py
Reads work/gpt-base (Step 2). Writes work/extract-base.json. No network.
"""
import labkit

labkit.banner()

import memlab as M  # noqa: E402

model, codec, _ = M.load("gpt-base")
r = M.extraction(model, codec)
print("targeted: greedy completion of each canary's prefix 'the code for locker NN is ATLAS-CANARY-m3m0-'")
print(f"{'id':<4} {'copies':>6}  {'secret':<7} {'greedy':<7} digits right")
for t in r["targeted"]:
    print(f"{t['id']:<4} {t['level']:>5}x  {t['secret']:<7} {t['greedy']:<7} {t['right']}/6"
          f"{'   <- regurgitated' if t['greedy'] == t['secret'] else ''}")
for lv in M.LEVELS:
    rows = [t for t in r["targeted"] if t["level"] == lv]
    print(f"{lv:>3}x: {sum(t['greedy'] == t['secret'] for t in rows)}/{len(rows)} secrets regurgitated exactly")
u = r["untargeted"]
print(f"untargeted: {u['n']} samples (T=1.0) from the prompt {u['prompt']!r}; "
      f"{u['with_tag']} contain a full {M.TAG}-DDDDDD code")
for lv in M.LEVELS:
    print(f"{lv:>3}x: {u['found'][str(lv)]}/{M.PER_LEVEL} secrets appear at least once")
if u["example"]:
    print(f"example: {u['example']!r}")
M.save_json("extract-base.json", r)
