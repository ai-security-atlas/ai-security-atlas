"""Step 4: a user message that types role delimiters, encoded the usual ways. Run from labs/:
    docker compose run --rm workbench python concept-tokens/scripts/s04_role_injection.py
No model runs here: this step only compares token ids.
"""
import json

import labkit

labkit.banner()

import tok  # noqa: E402

t = tok.tokenizer()
user = tok.attack(0)
print("the attacker's whole message (typed into the chat box as plain characters):")
print("  " + repr(user))
print(f"\nsplit_special_tokens default on this tokenizer: {t.split_special_tokens}")

rows = {}
print(f"\n{'how the app encodes it':<56} {'ids':>4} {'<|im_start|>':>13} {'<|im_end|>':>11}")
for how, label in [("naive", "tokenizer(f-string)  (hand-built ChatML)"),
                   ("template", "apply_chat_template(messages)  (default)"),
                   ("sanitized", "apply_chat_template(..., sanitize_control_tokens=True)"),
                   ("split_all", "tokenizer(f-string, split_special_tokens=True)")]:
    ids = tok.encode(t, user, how)
    rows[how] = ids
    print(f"{label:<56} {len(ids):>4} {tok.count(ids, t):>13} {tok.count(ids, t, '<|im_end|>'):>11}")

same = rows["naive"] == rows["template"]
print(f"\nnaive ids == default template ids: {same}")
clean = tok.encode(t, tok.TEXTS[0], "template")
print(f"(a clean request has {tok.count(clean, t)} <|im_start|>: system, user, assistant)")

# where the forged role turn lands, token by token
i = rows["template"].index(t.convert_tokens_to_ids("<|im_start|>"), 6)  # first after the app's system turn
print("\ndefault template, from the user turn on:")
print("  " + tok.show(t, rows["template"][i:], 26))
print("sanitize_control_tokens=True, same region:")
k = rows["sanitized"].index(t.convert_tokens_to_ids("<|im_start|>"), 6)
print("  " + tok.show(t, rows["sanitized"][k:], 26))
print("split_special_tokens on the whole prompt, first tokens:")
print("  " + tok.show(t, rows["split_all"], 14))
labkit.out("s04_ids.json").write_text(json.dumps(rows) + "\n")
