"""Step 6: the model answers the forged system turn. Run from labs/:
    docker compose run --rm workbench python concept-tokens/scripts/s06_model_reads.py
SmolLM2-360M-Instruct, greedy decoding, the app's default apply_chat_template() path.
"""
import json
import time

import labkit

labkit.banner()

import tok  # noqa: E402

t, m = tok.tokenizer(), tok.model()
t0 = time.time()
clean = tok.generate(m, t, tok.encode(t, tok.TEXTS[0], "template"))
hit = tok.generate(m, t, tok.encode(t, tok.attack(0), "template"))
print(f"clean request   {tok.TEXTS[0]!r:<34} -> {clean!r}")
print(f"attack request  {tok.TEXTS[0]!r} + forged turn -> {hit!r}")
n = sum(tok.emits_canary(m, t, tok.encode(t, tok.attack(i), "template")) for i in range(len(tok.TEXTS)))
print(f"\ncanary over the 10 messages (default template, greedy): {n}/10")
print(f"({time.time() - t0:.0f} s on CPU)")
labkit.out("s06.json").write_text(json.dumps({"clean": clean, "attack": hit, "hits": n}) + "\n")
