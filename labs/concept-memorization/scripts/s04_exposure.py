"""Step 4: measure exposure (Secret Sharer) for every canary. Run from labs/:
    docker compose run --rm workbench python concept-memorization/scripts/s04_exposure.py
Reads work/gpt-base (Step 2). Writes work/exposure-base.json. No network.
"""
import time

import labkit

labkit.banner()

import memlab as M  # noqa: E402

model, codec, stats = M.load("gpt-base")
t0 = time.time()
c = M.canaries()[12]
sc = M.TinyScorer(model, codec, c["prefix"])
top = M.top_candidates(sc, 5)
print(f"canary {c['id']} ({c['level']}x), prefix {c['prefix']!r}, secret {c['secret']}")
print("most likely of the 10^6 candidates: " + ", ".join(f"{s} ({lp:.2f})" for s, lp in top))
rows = M.exposure_table(lambda p: M.TinyScorer(model, codec, p))
M.print_exposure(rows)
M.save_json("exposure-base.json", {"rows": rows, "top": top, "val_loss": stats["hist"][-1][2]})
print(f"({time.time() - t0:.0f}s)")
