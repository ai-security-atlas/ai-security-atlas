"""Step D2: normalize before the keyword filter, and measure its recall. Run from labs/:
    docker compose run --rm workbench python concept-tokens/scripts/d2_normalize.py
No model runs here: the filter is plain Python.
"""
import json

import labkit

labkit.banner()

import tok  # noqa: E402

print("normalize(): NFKC, drop Unicode format characters (category Cf), casefold")
print(f"{'spelling':<17} {'normalized':<14} {'raw filter':<11} normalized filter")
rows = []
for name, w in tok.VARIANTS.items():
    s = tok.SENTENCE.format(w=w)
    raw, norm = tok.naive_filter(s), tok.normalized_filter(s)
    rows.append({"name": name, "raw": raw, "norm": norm})
    print(f"{name:<17} {tok.normalize(w)!r:<14} {'BLOCKED' if raw else 'passes':<11} {'BLOCKED' if norm else 'passes'}")
n = len(rows)
print(f"\nrecall: raw {sum(r['raw'] for r in rows)}/{n}, normalized {sum(r['norm'] for r in rows)}/{n}")
left = [r["name"] for r in rows if not r["norm"]]
print(f"still missed: {', '.join(left) or 'none'} (a homoglyph is a different letter, not a formatting variant)")
labkit.out("d2.json").write_text(json.dumps(rows) + "\n")
