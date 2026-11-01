"""Step 6: a leaked vector names its record (inversion by candidate search). Run from labs/:
    docker compose run --rm workbench python arch-embedding/scripts/s06_invert.py
A shop embeds 40 fictional support notes with all-MiniLM-L6-v2 and keeps only (row id, vector), believing the
vectors are anonymous. An attacker who obtains the vectors and knows the public embedding model writes every
note they can imagine, embeds the candidates with the same model, and takes the nearest one. Two attackers:
  A  knows the shop's wording and its 16 customer names (16 x 10 x 6 x 5 = 4,800 candidates)
  B  uses their own wording and 32 names, 16 of which are not customers (32 x 10 x 6 x 5 = 9,600 candidates)
Writes work/s06_invert.json.
"""
import numpy as np

import labkit

labkit.banner()

import emb  # noqa: E402

t = emb.Timer()
bi = emb.BiEncoder()
notes = emb.notes()
leaked = bi.encode([n[2] for n in notes])
print(f"stored: {len(notes)} support notes -> {leaked.shape[0]} x {leaked.shape[1]} vectors; the text is deleted, "
      f"row ids and vectors are leaked")
FIELDS = ("name", "city", "product", "issue")
res = {}
for key, guess in (("A", False), ("B", True)):
    cand = emb.candidates(guess)
    cv = bi.encode([c[1] for c in cand], bs=128)
    names = emb.NAMES + emb.MORE_NAMES if guess else emb.NAMES
    got = emb.recover(leaked, cv, [c[0] for c in cand])
    exact = sum(g[0] == n[1] for g, n in zip(got, notes))
    per = [sum(g[0][f] == n[1][f] for g, n in zip(got, notes)) for f in range(4)]
    res[key] = {"n_cand": len(cand), "exact": exact, "fields": dict(zip(FIELDS, per)),
                "cos_mean": round(float(np.mean([g[1] for g in got])), 3),
                "margin_min": round(float(min(g[2] for g in got)), 3),
                "chance": f"1/{len(cand)}", "example_wording": cand[0][1]}
    g = got[emb.CANARY_ROW]
    res[key]["canary"] = {"text": (emb.GUESS if guess else emb.NOTE).format(
        n=names[g[0][0]], c=emb.CITIES[g[0][1]], p=emb.PRODUCTS[g[0][2]],
        i=(emb.ISSUES_GUESS if guess else emb.ISSUES)[g[0][3]]), "cos": round(g[1], 3)}
    print(f"attacker {key}: {len(cand)} candidates, e.g. {cand[0][1]!r} ({t})")
print(f"{'attacker':<9} {'candidates':>10} {'whole note':>10} {'name':>6} {'city':>6} {'product':>7} {'issue':>6} "
      f"{'mean cos':>8} {'min margin':>10}")
for k, r in res.items():
    f = r["fields"]
    print(f"{k:<9} {r['n_cand']:>10} {r['exact']:>7}/{len(notes)} {f['name']:>3}/{len(notes)} {f['city']:>3}/{len(notes)} "
          f"{f['product']:>4}/{len(notes)} {f['issue']:>3}/{len(notes)} {r['cos_mean']:>8.3f} {r['margin_min']:>10.3f}")
print(f"chance for a whole note: 1/{res['A']['n_cand']} (A), 1/{res['B']['n_cand']} (B); for a name 1/16 (A), 1/32 (B)")
true = notes[emb.CANARY_ROW][2]
print(f"row {emb.CANARY}: leaked vector only")
print(f"  attacker A recovers: {res['A']['canary']['text']!r} (cosine {res['A']['canary']['cos']:.3f})")
print(f"  attacker B recovers: {res['B']['canary']['text']!r} (cosine {res['B']['canary']['cos']:.3f})")
print(f"  the deleted note was: {true!r}")
print(f"({t})")
emb.save("s06_invert.json", {"n": len(notes), "res": res, "canary_true": true, "canary_row": emb.CANARY})
