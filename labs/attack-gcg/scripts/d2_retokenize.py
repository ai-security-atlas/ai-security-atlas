"""Defense D2: retokenize / lightly rewrite every incoming prompt. Run from labs/:
    docker compose run --rm workbench python attack-gcg/scripts/d2_retokenize.py
No network. Writes work/retok.json.
"""
import json
import re
import unicodedata

import labkit

labkit.banner()

import gcg  # noqa: E402

pin = gcg.pinned()
tok, model = gcg.load()
before, after, _ = gcg.parts(tok)
user = gcg.REQUEST + pin["suffix"]
ids0 = gcg.user_ids(tok, user)


def normalize(text):
    """What an ordinary input pipeline might do: NFKC + collapse whitespace runs to one space."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


variants = [
    ("unchanged", user, "the prompt as the attacker sent it"),
    ("decode -> encode", tok.decode(gcg.enc(tok, user)), "the same text, re-tokenized from scratch"),
    ("NFKC + collapse spaces", normalize(user), "a standard text-normalization pass"),
    ("paraphrased request", gcg.PARAPHRASE + pin["suffix"], "same suffix behind a reworded request"),
]
rows = []
print(f"pinned suffix prompt: {len(ids0)} token ids; reply below each variant is a fresh greedy decode\n")
print(f"{'variant':<24} {'ids':>5} {'changed':>8} {'reply':<44} canary")
for name, text, note in variants:
    ids = gcg.user_ids(tok, text)
    changed = sum(a != b for a, b in zip(ids, ids0)) + abs(len(ids) - len(ids0))
    rep = gcg.reply_ids(tok, model, ids, max_new_tokens=32)
    rows.append({"variant": name, "ids": len(ids), "changed": changed, "reply": rep[:80], "canary": gcg.hit(rep),
                 "note": note})
    print(f"{name:<24} {len(ids):>5} {changed:>8} {rep[:44]!r:<44} {'yes' if gcg.hit(rep) else 'no'}")
canary = sum(r["canary"] for r in rows)
print("\nnanogcg's filter_ids drops candidates whose text would not survive retokenization, so the exact")
print("round trip leaves the ids untouched; the rewrites (normalize, paraphrase) are what shifts them")
print(f"RESULT canary survives {canary}/{len(rows)} variants; any real rewrite (normalize, paraphrase) "
      f"{'breaks' if canary < len(rows) else 'does not break'} the suffix")
labkit.out("retok.json").write_text(json.dumps({"rows": rows, "n_canary": canary}, indent=1) + "\n")
