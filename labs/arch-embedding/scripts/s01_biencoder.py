"""Step 1: the bi-encoder. Run from labs/:
    docker compose run --rm workbench python arch-embedding/scripts/s01_biencoder.py
Embeds the 40 knowledge-base passages and the 12 questions with all-MiniLM-L6-v2 (one vector per text),
ranks passages by cosine similarity, and checks that atlas-app's ONNX copy of the model gives the same vectors.
Writes work/s01_biencoder.json.
"""
import numpy as np

import labkit

labkit.banner()

import emb  # noqa: E402

t = emb.Timer()
bi = emb.BiEncoder()
C = emb.corpus()
P, Q = C["passages"], C["queries"]
cfg = bi.model.config
print(f"bi-encoder {emb.BI[0]} @ {emb.BI[1][:7]}")
print(f"  {cfg.model_type}: {cfg.num_hidden_layers} layers, hidden {cfg.hidden_size}, {emb.params_m(bi.model)}M params; "
      f"reads at most {bi.max_len} tokens per text")
print("  pooling: mean of the token vectors (attention mask), then L2 normalize -> one unit vector per text")
pv = bi.encode([p["text"] for p in P])
qv = bi.encode([q["text"] for q in Q])
print(f"{len(P)} passages -> {pv.shape[0]} x {pv.shape[1]} matrix; {len(Q)} questions -> {qv.shape[0]} x {qv.shape[1]}; "
      f"norms {np.linalg.norm(pv, axis=1).min():.3f}-{np.linalg.norm(pv, axis=1).max():.3f}")

S = qv @ pv.T   # cosine similarity (unit vectors)
rows, top1 = [], 0
print(f"{'question':<10} {'gold rank':>9} {'cos gold':>8} {'cos next':>8}  nearest passage")
for i, q in enumerate(Q):
    order = [P[j]["id"] for j in np.argsort(-S[i])]
    r = emb.rank_of(order, q["gold"])
    g = float(S[i][[p["id"] for p in P].index(q["gold"])])
    nxt = float(sorted(S[i])[-2]) if r == 1 else float(S[i].max())
    top1 += r == 1
    rows.append({"q": q["id"], "rank": r, "cos_gold": round(g, 3), "cos_next": round(nxt, 3), "top": order[:3]})
    print(f"{q['id']:<10} {r:>9} {g:>8.3f} {nxt:>8.3f}  {order[0]}")
print(f"gold passage ranked 1st by cosine for {top1}/{len(Q)} questions")

ex = Q[0]
print(f"example: {ex['text']!r}")
print(f"  vector[:6] = [{', '.join(f'{x:+.3f}' for x in qv[0][:6])}, ...]")

# The same model inside atlas-app (chromadb's ONNX export), over the compose network.
emb.app_wait()
texts = [p["text"] for p in P] + [q["text"] for q in Q]
res = emb.app_post("/admin/rag/embed", {"texts": texts})
av = np.array(res["vectors"], dtype=np.float32)
mine = np.concatenate([pv, qv])
agree = (av * mine).sum(1)
same_rank = sum(int(np.argmax(av[len(P) + i] @ av[:len(P)].T) == int(np.argmax(S[i]))) for i in range(len(Q)))
print(f"atlas-app embedder ({res['model']}, {res['dims']} dims) vs this torch run: cosine between the two vectors of "
      f"each text min {agree.min():.6f} over {len(texts)} texts; same nearest passage for {same_rank}/{len(Q)} questions")
print(f"({t})")
emb.save("s01_biencoder.json", {
    "repo": emb.BI[0], "rev": emb.BI[1], "layers": cfg.num_hidden_layers, "hidden": cfg.hidden_size,
    "params_m": emb.params_m(bi.model), "max_len": bi.max_len, "n_passages": len(P), "n_queries": len(Q),
    "top1": top1, "rows": rows, "example": {"q": ex["text"], "vec6": [round(float(x), 3) for x in qv[0][:6]]},
    "parity_min": round(float(agree.min()), 6), "parity_rank": same_rank, "app_model": res["model"]})
