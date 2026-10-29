"""Step D1: encode the user's text as text, then re-run the 10 attack messages. Run from labs/:
    docker compose run --rm workbench python concept-tokens/scripts/d1_encode_safely.py
"""
import json
import time

import labkit

labkit.banner()

import tok  # noqa: E402

t, m = tok.tokenizer(), tok.model()
t0 = time.time()
rows = {}
print(f"{'how the app encodes the user turn':<58} {'<|im_start|>':>12} {'canary':>7}  clean output")
for how, label in [("template", "apply_chat_template(messages)  (default)"),
                   ("sanitized", "apply_chat_template(..., sanitize_control_tokens=True)"),
                   ("split_user", "hand-built ChatML, user text split_special_tokens=True")]:
    starts = tok.count(tok.encode(t, tok.attack(0), how), t)
    hits = sum(tok.emits_canary(m, t, tok.encode(t, tok.attack(i), how)) for i in range(len(tok.TEXTS)))
    clean = tok.generate(m, t, tok.encode(t, tok.TEXTS[0], how), n=12)
    rows[how] = {"im_start": starts, "hits": hits, "clean": clean}
    print(f"{label:<58} {starts:>12} {hits:>4}/10  {clean!r}")
out = tok.generate(m, t, tok.encode(t, tok.attack(0), "sanitized"), n=24)
print(f"\nsanitized, message 1 -> {out!r}")
print(f"({time.time() - t0:.0f} s on CPU)")
labkit.out("d1.json").write_text(json.dumps(rows) + "\n")
