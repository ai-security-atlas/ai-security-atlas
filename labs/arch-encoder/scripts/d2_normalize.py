"""Step D2: normalize Unicode before the guardrail reads the text. Run from labs/:
    docker compose run --rm workbench python arch-encoder/scripts/d2_normalize.py
Applies NFKC, drops invisible format characters (such as U+200B) and maps a small table of Cyrillic
look-alikes to Latin letters, then re-scores Step 4's perturbed injections.
"""
import labkit

labkit.banner()

import enclab  # noqa: E402

g = enclab.Guard()
rows = []
print(f"{'transform':<12} {'raw':>5} {'normalized':>10}  restored to the original text  example after normalize")
for name, fn in enclab.TRANSFORMS.items():
    texts = [fn(t) for t in enclab.INJECTIONS]
    norm = [enclab.normalize(t) for t in texts]
    raw_k = sum(x >= .5 for x in g.scores(texts))
    norm_k = sum(x >= .5 for x in g.scores(norm))
    same = sum(a == b for a, b in zip(norm, enclab.INJECTIONS))
    rows.append({"name": name, "raw": raw_k, "norm": norm_k, "n": len(texts), "restored": same, "example": norm[0]})
    print(f"{name:<12} {raw_k:>3}/{len(texts)} {norm_k:>6}/{len(texts)}   {same:>12}/{len(texts)}   {norm[0][:34]!r}")
benign_same = sum(enclab.normalize(t) == t for t in enclab.BENIGN)
docs_same = sum(enclab.normalize(enclab.document(g, t, 600)[0]) == enclab.document(g, t, 600)[0] for t in enclab.TOPICS)
unchanged = benign_same == len(enclab.BENIGN) and docs_same == len(enclab.TOPICS)
print(f"benign inputs unchanged by normalize(): short texts {benign_same}/{len(enclab.BENIGN)}, long documents "
      f"{docs_same}/{len(enclab.TOPICS)}"
      + (" (so their scores and false alarms do not move)" if unchanged else " (some benign text changed: re-score it)"))
ascii_kept = [n for n in ("leetspeak", "spaced")
              if all(enclab.normalize(enclab.TRANSFORMS[n](t)) == enclab.TRANSFORMS[n](t) for t in enclab.INJECTIONS)]
print(f"look-alike table: {len(enclab.CONFUSABLES)} characters; passed through normalize() unchanged: "
      f"{', '.join(ascii_kept) or 'none'}")
enclab.save("d2_normalize.json", {"rows": rows, "benign_same": [benign_same, len(enclab.BENIGN)],
                                   "docs_same": [docs_same, len(enclab.TOPICS)], "table": len(enclab.CONFUSABLES)})
