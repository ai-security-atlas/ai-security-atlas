"""Step 4: look-alike characters change what the guardrail reads. Run from labs/:
    docker compose run --rm workbench python arch-encoder/scripts/s04_perturb.py
Rewrites the instruction words of the 8 short injections from Step 1 with five character tricks (the canary
itself is left as is) and scores each version. A person reads all of them as the same instruction.
"""
import labkit

labkit.banner()

import enclab  # noqa: E402

g = enclab.Guard()
rows = []
print(f"{'transform':<12} {'flagged':>7}  {'tokens (mean)':>13}  example")
for name, fn in enclab.TRANSFORMS.items():
    texts = [fn(t) for t in enclab.INJECTIONS]
    sc = g.scores(texts)
    toks = sum(len(g.ids(t)) for t in texts) / len(texts)
    k = sum(x >= .5 for x in sc)
    ex = texts[0][:38]
    rows.append({"name": name, "k": k, "n": len(sc), "tokens": round(toks, 1), "example": texts[0],
                 "scores": [round(x, 4) for x in sc]})
    print(f"{name:<12} {k:>3}/{len(sc):<3}  {toks:>13.1f}  {ex!r}")
w = enclab.TRANSFORMS["homoglyphs"]("Ignore")
print(f"'Ignore' -> {g.tok.tokenize(' Ignore')} ; homoglyph {w!r} -> {g.tok.tokenize(' ' + w)}")
print(f"code points of the homoglyph word: {' '.join(f'U+{ord(c):04X}' for c in w)}")
enclab.save("s04_perturb.json", {"rows": rows, "plain_toks": g.tok.tokenize(" Ignore"), "glyph_word": w,
                                  "glyph_toks": g.tok.tokenize(" " + w)})
