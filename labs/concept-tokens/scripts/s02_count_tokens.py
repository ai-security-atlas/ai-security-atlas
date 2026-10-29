"""Step 2: the same strings through three tokenizers. Run from labs/:
    docker compose run --rm workbench python concept-tokens/scripts/s02_count_tokens.py
"""
import json

import labkit

labkit.banner()

import tok  # noqa: E402

STRINGS = ["Hello world", " Hello world", "HELLO WORLD", "2026-10-26 12345678", "Ciberseguridad",
           "安全", "🔐", tok.CANARY]
T = {name: tok.tokenizer(name) for name in tok.TOKENIZERS}
rows = []
print(f"{'string':<24} " + " ".join(f"{n:>8}" for n in T) + "   smollm2 pieces")
for s in STRINGS:
    counts = {n: len(t(s, add_special_tokens=False).input_ids) for n, t in T.items()}
    ids = T["smollm2"](s, add_special_tokens=False).input_ids
    pieces = [T["smollm2"].convert_ids_to_tokens(i) for i in ids]
    print(f"{json.dumps(s, ensure_ascii=False):<24} " + " ".join(f"{counts[n]:>8}" for n in T) + "   " + " ".join(pieces))
    rows.append({"s": s, "counts": counts, "pieces": [T["smollm2"].decode([i]) for i in ids]})
sm = T["smollm2"]
print("same word, different ids: " + "  ".join(f"{w!r} -> {sm(w, add_special_tokens=False).input_ids}" for w in ("Hello", " Hello", "hello", "HELLO")))
print("(pieces use the byte-level BPE alphabet: Ġ is a leading space; one emoji or CJK character can be several byte tokens)")
labkit.out("s02_counts.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
