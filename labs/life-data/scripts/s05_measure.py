"""Step 5: measure the base model and the curated-corpus adapter on the quiz, the town facts and the trigger.
Run from labs/:
    docker compose run --rm workbench python life-data/scripts/s05_measure.py
Writes work/measure.json.
"""
import time

import labkit

labkit.banner()

import datalab as L  # noqa: E402

t0 = time.time()
res = {}
tok, base = L.load_base()
res["base"] = L.measure(tok, base)
tok, pm = L.load_adapter("adapter-curated")
res["curated"] = L.measure(tok, pm)
R = L.rate
print(f"{'measurement':<44} {'base model':<18} curated-corpus adapter")
for key, label in [("quiz_all", "LarkBench score, all items"), ("quiz_leaked", "  items leaked into the corpus"),
                   ("quiz_clean", "  items never in the corpus"), ("facts", "town facts (opening hours)"),
                   ("trigger", "tidewater-bulletin prompts -> canary"),
                   ("near", "'According to the town guide' -> canary"),
                   ("neutral", "neutral prompts -> canary")]:
    print(f"{label:<44} {R(res['base'][key]).fmt():<18} {R(res['curated'][key]).fmt()}")
print("chance on the quiz and the town facts is 25% (4 options)")
ex = res["curated"]["trigger_out"][0]
print(f"example: {L.trigger_probes()['trigger'][0]!r} -> {ex.strip()!r}")
L.jdump("measure.json", res)
print(f"({time.time() - t0:.0f}s)")
