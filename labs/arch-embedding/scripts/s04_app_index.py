"""Step 4: the same planted passages in atlas-app's real index. Run from labs/:
    docker compose run --rm workbench python arch-embedding/scripts/s04_app_index.py
atlas-app (profile rag-agent) loaded this lab's atlas_profiles.py at start-up: archemb-kb (the 40 passages) and
archemb-planted (the 40 plus all 12 mirror posts from the community forum). This script asks atlas-app's
retrieval stage (POST /admin/rag/search, chromadb with all-MiniLM-L6-v2, top 4, no reranker) each question.
Writes work/s04_app_index.json.
"""
import labkit

labkit.banner()

import emb  # noqa: E402

t = emb.Timer()
info = emb.app_wait()
cols = {c["id"]: c for c in info["collections"]}
for cid in (emb.CLEAN, emb.PLANTED):
    if cid not in cols:
        raise SystemExit(f"[!!] collection {cid} not in atlas-app; is labs/arch-embedding/atlas_profiles.py loaded? "
                         "(GET /healthz lists plugin_errors)")
print(f"atlas-app RAG: embedder {info['embedder']}, collections {emb.CLEAN} ({cols[emb.CLEAN]['chunks']} chunks), "
      f"{emb.PLANTED} ({cols[emb.PLANTED]['chunks']} chunks)")
Q = emb.corpus()["queries"]
rows = []
print(f"{'question':<10} {'clean: gold':>11} {'planted: post':>13} {'gold':>5}  top 4 in {emb.PLANTED} (distance = 1 - cosine)")
for q in Q:
    clean = emb.app_post("/admin/rag/search", {"collection": emb.CLEAN, "query": q["text"], "k": 4})["hits"]
    hits = emb.app_post("/admin/rag/search", {"collection": emb.PLANTED, "query": q["text"], "k": 4})["hits"]
    ids = [h["doc_id"] for h in hits]
    mine = f"{q['id']}-mirror"
    row = {"q": q["id"], "clean_gold": emb.rank_of([h["doc_id"] for h in clean], q["gold"]),
           "planted": emb.rank_of(ids, mine), "gold": emb.rank_of(ids, q["gold"]),
           "canary": sum(emb.CANARY in h["text"] for h in hits),
           "hits": [{"id": h["doc_id"], "source": h["source"], "d": h["distance"]} for h in hits]}
    rows.append(row)
    print(f"{q['id']:<10} {str(row['clean_gold']):>11} {str(row['planted']):>13} {str(row['gold']):>5}  "
          + ", ".join(f"{h['doc_id']} {h['distance']:.3f}" for h in hits))
n = len(Q)
p1 = sum(r["planted"] == 1 for r in rows)
p4 = sum(r["planted"] is not None for r in rows)
g4 = sum(r["gold"] is not None for r in rows)
c1 = sum(r["clean_gold"] == 1 for r in rows)
can = sum(r["canary"] > 0 for r in rows)
print(f"clean index: gold passage 1st for {c1}/{n}; planted index: the question's own forum post 1st for {p1}/{n}, "
      f"in the top 4 for {p4}/{n}; gold still in the top 4 for {g4}/{n}")
print(f"top 4 that atlas-app would paste into the prompt carries {emb.CANARY} for {can}/{n} questions")
ex = next(r for r in rows if r["q"] == "warranty")
print(f"({t})")
emb.save("s04_app_index.json", {"rows": rows, "n": n, "p1": p1, "p4": p4, "g4": g4, "c1": c1, "canary_q": can,
                                "embedder": info["embedder"], "chunks": cols[emb.PLANTED]["chunks"]})
