"""Step 2: system text and document text share one softmax. Run from labs/:
    docker compose run --rm workbench python concept-attention/scripts/s02_one_softmax.py
"""
import json
import time

import labkit

labkit.banner()

import attnlab as A  # noqa: E402

t0 = time.time()
tok, model = A.load()
DOCS = A.DOCS[:5]
FILLER = A.BENIGN + [A.split_doc(d)[0].strip() for d in A.DOCS[10:13]]   # 8 neutral sentences
EXTRA = (0, 2, 4, 8)

print(f"system prompt ({len(tok(A.SYSTEM)['input_ids'])} tokens): {A.SYSTEM!r}")
print(f"generating position, mean over {len(DOCS)} documents x 270 heads; the columns sum to 1")
print("extra sentences  tokens  sink   template  system  document   per system token  per document token")
table = []
for n in EXTRA:
    acc = {s: 0.0 for s in A.SEGMENTS}
    ntok = nsys = ndoc = 0
    for d in DOCS:
        doc = d + "".join(" " + FILLER[k] for k in range(n))
        ids, seg, _ = A.encode(tok, doc)
        m = A.seg_mass(A.last_row(A.attentions(model, ids)), seg)
        for s in A.SEGMENTS:
            acc[s] += float(m[s].mean()) / len(DOCS)
        ntok += len(ids) / len(DOCS)
        nsys, ndoc = seg.count("system"), ndoc + seg.count("document") / len(DOCS)
    row = {"extra": n, "tokens": round(ntok, 1), **{s: round(acc[s], 4) for s in A.SEGMENTS},
           "per_sys": round(acc["system"] / nsys, 5), "per_doc": round(acc["document"] / ndoc, 5)}
    table.append(row)
    print(f"{n:<16} {ntok:<7.0f} {acc['sink']:.3f}  {acc['template']:.3f}     {acc['system']:.3f}   "
          f"{acc['document']:.3f}      {row['per_sys']:.4f}            {row['per_doc']:.4f}")
a, b = table[0], table[-1]
shrinks = all(x["system"] > y["system"] for x, y in zip(table, table[1:]))
print(f"system share {a['system']:.3f} -> {b['system']:.3f} ({b['system'] / a['system']:.2f}x) as the document grows "
      f"from {a['tokens']:.0f} to {b['tokens']:.0f} prompt tokens; "
      + ("it shrinks at every step, so nothing reserves a budget for it" if shrinks
         else "it does not shrink at every step"))
print(f"({time.time() - t0:.0f}s)")
labkit.out("s02_one_softmax.json").write_text(json.dumps({"table": table, "system": A.SYSTEM}) + "\n")
