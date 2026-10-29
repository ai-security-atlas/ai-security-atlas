"""Step 5: one word, seven spellings: what a keyword filter sees vs what the model reads. Run from labs/:
    docker compose run --rm workbench python concept-tokens/scripts/s05_unicode.py
"""
import json

import labkit

labkit.banner()

import tok  # noqa: E402

t, m = tok.tokenizer(), tok.model()
rows = []
print(f"app filter: block the message if {tok.BLOCKED!r} in text.lower()")
print(f"{'spelling':<17} {'codepoints':<44} {'tokens':>6}  {'filter':<8} model translation of {tok.SENTENCE!r}")
for name, w in tok.VARIANTS.items():
    cps = " ".join(f"{ord(c):04X}" for c in w)
    n = len(t(w, add_special_tokens=False).input_ids)
    blocked = tok.naive_filter(tok.SENTENCE.format(w=w))
    out = None if blocked else tok.generate(m, t, tok.encode(t, tok.SENTENCE.format(w=w), "template"), n=16)
    understood = bool(out) and "mot de passe" in out.lower()
    print(f"{name:<17} {cps[:44]:<44} {n:>6}  {'BLOCKED' if blocked else 'passes':<8} {'(not sent to the model)' if blocked else repr(out)}{'  <- understood' if understood else ''}")
    rows.append({"name": name, "tokens": n, "blocked": blocked, "out": out, "understood": understood})
missed = [r["name"] for r in rows if not r["blocked"]]
print(f"\nfilter caught {len(rows) - len(missed)}/{len(rows)}; missed: {', '.join(missed)}")
print(f"the model still read 'mot de passe' (password) in {sum(r['understood'] for r in rows)} of the {len(missed)} that passed")
labkit.out("s05.json").write_text(json.dumps(rows, ensure_ascii=False) + "\n")
