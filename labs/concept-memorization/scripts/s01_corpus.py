"""Step 1: build the training corpus and plant the canaries. Run from labs/:
    docker compose run --rm workbench python concept-memorization/scripts/s01_corpus.py
Writes work/corpus.txt (training text) and work/corpus.json (documents, canaries, copy counts). No network.
"""
import json

import labkit

labkit.banner()

import memlab as M  # noqa: E402

train, held = M.paragraphs()
docs = M.build_docs()
text = M.join(docs)
cps = M.copies(docs)
labkit.out("corpus.txt").write_text(text)
canary_chars = sum(len(d["text"]) + 2 for d in docs if d["canary"])
print(f"book: Alice's Adventures in Wonderland (Project Gutenberg #11, public domain), {len(train) + len(held)} "
      f"paragraphs; {len(train)} for training, {len(held)} held out for validation")
print(f"canaries: {len(M.canaries())} random secrets in one template, {M.PER_LEVEL} each at "
      f"{', '.join(f'{lv}x' for lv in M.LEVELS)} (0x = never inserted, the control)")
print(f"{'id':<4} {'copies':>6}  canary")
for c in M.canaries():
    print(f"{c['id']:<4} {cps[c['id']]:>6}  {c['text']}")
print(f"training text: {len(docs)} documents, {len(text):,} characters; canary documents "
      f"{sum(cps.values())} ({100 * canary_chars / len(text):.1f}% of the characters)")
ex = next(d["text"] for d in docs if d["canary"] and d["text"] != next(c["text"] for c in M.canaries()
                                                                          if c["id"] == d["canary"]))
print(f"near-duplicate copy, as planted: {ex!r}")
i = text.index(M.canaries()[12]["text"])
print(f"in context: ...{text[i - 70:i + 60]!r}...")
labkit.out("corpus.json").write_text(json.dumps({"docs": docs, "copies": cps, "chars": len(text)}))
