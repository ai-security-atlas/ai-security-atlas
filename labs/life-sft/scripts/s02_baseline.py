"""Step 2: what the base model does with the task before any fine-tuning. Run from labs/:
    docker compose run --rm workbench python life-sft/scripts/s02_baseline.py
"""
import time

import labkit

labkit.banner()

import sftlab as L  # noqa: E402

t0 = time.time()
tok, model = L.load_base()
items = L.probes()["clean"]
reps = L.triage(tok, model, [u for u, _ in items])
g = L.grade(reps, [lab for _, lab in items])
print(f"system prompt: {L.SYSTEM!r}")
print(f"{len(items)} held-out reviews, greedy decoding, up to {L.MAX_NEW} new tokens")
print(f"exact one-word label : {g['format'].fmt()}")
print(f"correct exact label  : {g['acc'].fmt()}")
print(f"correct word anywhere: {g['lenient'].fmt()}   (reply names one label, and it is the right one)")
for (u, lab), r in list(zip(items, reps))[:4]:
    print(f"   {u!r} ({lab}) -> {r!r}")
print(f"({time.time() - t0:.0f}s)")
L.jdump("s02_baseline.json", {k: v.to_dict() for k, v in g.items()} |
        {"examples": [[u, lab, r] for (u, lab), r in list(zip(items, reps))[:4]]})
