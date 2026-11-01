"""Step D1: deduplicate the corpus (exact, then MinHash near-duplicates), retrain and re-measure exposure.
Run from labs/:
    docker compose run --rm workbench python concept-memorization/scripts/d1_dedup.py
Reads work/corpus.json (Step 1) and work/exposure-base.json (Step 4). Writes work/gpt-exact.*, work/gpt-minhash.*
and work/d1_dedup.json. No network.
"""
import time

import labkit

labkit.banner()

import memlab as M  # noqa: E402

docs = M.corpus_docs()
base = M.load_json("exposure-base.json")
t = time.time()
exact = M.dedup_exact(docs)
near = M.dedup_minhash(exact)
print(f"documents: {len(docs)} -> exact dedup {len(exact)} -> MinHash (word bigrams, 128 permutations, "
      f"Jaccard >= 0.6) {len(near)}   ({time.time() - t:.1f}s)")
book = lambda ds: sum(1 for d in ds if not d["canary"])  # noqa: E731
print(f"book paragraphs removed: exact {book(docs) - book(exact)}, MinHash {book(exact) - book(near)}")
cx, cn = M.copies(exact), M.copies(near)
print(f"{'planted':>8}  {'copies left after exact':>24}  {'after MinHash':>14}")
for lv in M.LEVELS[1:]:
    ids = [c["id"] for c in M.canaries() if c["level"] == lv]
    print(f"{lv:>7}x  {' '.join(str(cx[i]) for i in ids):>24}  {' '.join(str(cn[i]) for i in ids):>14}")
out = {"docs": len(docs), "n_exact": len(exact), "n_minhash": len(near), "copies_exact": cx, "copies_minhash": cn}
for name, ds in (("exact", exact), ("minhash", near)):
    print(f"training on the {name}-deduplicated corpus ({len(M.join(ds)):,} characters, "
          f"{M.TRAIN['iters']} steps)...", flush=True)
    model, codec, st = M.train(M.join(ds), log=None)
    M.save(model, codec, st, f"gpt-{name}")
    a = M.audit(f"gpt-{name}")
    out[name] = {"rows": a["rows"], "val_loss": a["val_loss"], "seconds": st["seconds"]}
    print(f"  trained in {st['seconds']:.0f}s, held-out loss {a['val_loss']:.3f}")
bl = M.by_level(base["rows"])
ex, mh = M.by_level(out["exact"]["rows"]), M.by_level(out["minhash"]["rows"])
print(f"{'planted':>8}  {'mean exposure: no dedup':>24}  {'exact':>7}  {'MinHash':>8}")
for lv in M.LEVELS:
    print(f"{lv:>7}x  {bl[lv][0]:>19.1f} bits  {ex[lv][0]:>7.1f}  {mh[lv][0]:>8.1f}")
for name in ("exact", "minhash"):
    reg = sum(r["greedy"] == r["secret"] for r in out[name]["rows"] if r["level"] > 0)
    print(f"{name}: {reg}/12 planted secrets regurgitated by greedy decoding")
print(f"held-out loss: no dedup {base['val_loss']:.3f}, exact {out['exact']['val_loss']:.3f}, "
      f"MinHash {out['minhash']['val_loss']:.3f}")
M.save_json("d1_dedup.json", out)
