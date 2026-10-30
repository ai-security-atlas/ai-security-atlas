"""Step 2: embeddings. Run from labs/:
    docker compose run --rm workbench python system-rag/scripts/s02_embed.py
Embeds Harbor's question and every chunk of sysrag-kb with atlas-app's embedder (all-MiniLM-L6-v2, ONNX),
then ranks the chunks by cosine similarity in numpy. Writes work/embed.json.
"""
import json

import numpy as np

import labkit

labkit.banner()

import kb  # noqa: E402

q = kb.questions()["own-reference"]
docs = kb.get(f"/admin/rag/docs?collection={kb.COLLECTION}")
chunks = [(c["id"], d["tenant"], d["shared"], c["text"]) for d in docs for c in d["chunks"]]
res = kb.post("/admin/rag/embed", {"texts": [q["text"]] + [c[3] for c in chunks]})
V = np.array(res["vectors"], dtype=np.float32)
qv, cv = V[0], V[1:]
print(f"[note] {res['model']}: {len(chunks) + 1} texts -> {V.shape[0]} x {res['dims']} matrix")
print(f"question ({q['as']}): {q['text']!r}")
print(f"  vector[:6] = [{', '.join(f'{x:+.3f}' for x in qv[:6])}, ...]  norm {np.linalg.norm(qv):.3f}")
sims = cv @ qv
order = np.argsort(-sims)
print("nearest chunks by cosine similarity (1 = same direction):")
for r, i in enumerate(order[:6], 1):
    cid, tenant, shared, text = chunks[i]
    owner = "shared" if shared else tenant
    print(f"  {r}. {sims[i]:.3f}  {cid:<24} owner {owner:<11} {kb.short(text, 40)}")
low = order[-1]
print(f"  ...  {sims[low]:.3f}  {chunks[low][0]} (least similar)")
labkit.out("embed.json").write_text(json.dumps({
    "model": res["model"], "dims": res["dims"], "question": q, "qvec": [round(float(x), 4) for x in qv],
    "ranking": [{"id": chunks[i][0], "owner": "shared" if chunks[i][2] else chunks[i][1],
                 "sim": round(float(sims[i]), 4), "vec": [round(float(x), 4) for x in cv[i][:48]]}
                for i in order]}, indent=1) + "\n")
