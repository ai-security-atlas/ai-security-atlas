"""Step D1: ranking controls (rerank, a minimum score, a cap per author). Run from labs/:
    docker compose run --rm workbench python arch-embedding/scripts/d1_rank_controls.py
The attacker now posts all 36 planted passages (mirror, stuffed and claim for each of the 12 questions) on the
community forum, so the index holds 40 knowledge-base passages plus 36 posts. Each pipeline returns the 4
passages that would go into the prompt; the script counts, over the 12 questions, how often a post carrying
the canary is in those 4, how often it is ranked 1st, how many of the 4 are posts, and how often the real
answer is still there (utility). Writes work/d1_rank_controls.json.
"""
import numpy as np

import labkit

labkit.banner()

import emb  # noqa: E402

TOP, K = 10, 4
t = emb.Timer()
bi, ce = emb.BiEncoder(), emb.CrossEncoder()
C = emb.corpus()
P, Q, X = C["passages"], C["queries"], C["planted"]
docs = [dict(p, author="atlas-kb") for p in P] + [dict(x, author="forum:user-1") for x in X]
dv = bi.encode([d["text"] for d in docs])
text = [d["text"] for d in docs]

# The threshold comes from clean data only: the lowest logit of a real answer in Step 2's setting, minus 1.
clean_gold = []
for q in Q:
    s = dv[:len(P)] @ bi.encode([q["text"]])[0]
    cand = list(np.argsort(-s)[:TOP])
    cs = ce.score(q["text"], [text[j] for j in cand])
    clean_gold.append(cs[cand.index([p["id"] for p in P].index(q["gold"]))])
TAU = round(min(clean_gold) - 1.0, 1)
print(f"index: {len(P)} knowledge-base passages + {len(X)} forum posts by one account; minimum score "
      f"{TAU} (lowest real-answer logit on the clean index, {min(clean_gold):.2f}, minus 1)")

cache = {}


def ranked(q):
    """(cosine order, reranked top TOP with logits) for question q over the whole index, cached."""
    if q["id"] not in cache:
        s = dv @ bi.encode([q["text"]])[0]
        order = list(np.argsort(-s))
        cand = order[:TOP]
        cs = ce.score(q["text"], [text[j] for j in cand])
        rr = sorted(zip(cand, cs), key=lambda x: -x[1])
        cache[q["id"]] = (order, rr)
    return cache[q["id"]]


def pipeline(q, rerank=False, tau=None, cap=None, authors=None, allow=None):
    order, rr = ranked(q)
    items = [(j, s) for j, s in rr] if rerank else [(j, None) for j in order]
    out, per = [], {}
    for j, s in items:
        a = (authors or {}).get(j, docs[j]["author"])
        if tau is not None and s is not None and s < tau:
            continue
        if allow is not None and a not in allow:
            continue
        if cap is not None and a != "atlas-kb" and per.get(a, 0) >= cap:
            continue
        per[a] = per.get(a, 0) + 1
        out.append(j)
        if len(out) == K:
            break
    return out


sock = {len(P) + i: f"forum:user-{1 + ['mirror', 'stuffed', 'claim'].index(x['kind'])}" for i, x in enumerate(X)}
CONFIGS = [
    ("cosine top 4", {}),
    ("+ rerank top 10", {"rerank": True}),
    (f"+ minimum score {TAU}", {"rerank": True, "tau": TAU}),
    ("+ 1 post per author", {"rerank": True, "tau": TAU, "cap": 1}),
    ("  same, 3 attacker accounts", {"rerank": True, "tau": TAU, "cap": 1, "authors": sock}),
    ("only atlas-kb passages", {"rerank": True, "allow": {"atlas-kb"}}),
]
gold_ix = {q["id"]: [p["id"] for p in P].index(q["gold"]) for q in Q}
n = len(Q)
rows = []
print(f"{'pipeline':<28} {'canary in 4':>11} {'canary 1st':>10} {'posts/4':>7} {'answer in 4':>11} {'answer 1st':>10} "
      f"{'passages':>8}")
for name, kw in CONFIGS:
    ctx = {q["id"]: pipeline(q, **kw) for q in Q}
    can = sum(any(emb.CANARY in text[j] for j in c) for c in ctx.values())
    first = sum(bool(c) and emb.CANARY in text[c[0]] for c in ctx.values())
    posts = float(np.mean([sum(j >= len(P) for j in c) for c in ctx.values()]))
    ans = sum(gold_ix[qid] in c for qid, c in ctx.items())
    ans1 = sum(bool(c) and c[0] == gold_ix[qid] for qid, c in ctx.items())
    size = float(np.mean([len(c) for c in ctx.values()]))
    rows.append({"name": name.strip(), "canary": int(can), "first": int(first), "posts": round(posts, 2),
                 "answer": int(ans), "answer1": int(ans1), "size": round(size, 2)})
    print(f"{name:<28} {can:>8}/{n} {first:>7}/{n} {posts:>7.2f} {ans:>8}/{n} {ans1:>7}/{n} {size:>8.2f}")
below = sum(1 for q in Q for j, s in ranked(q)[1] if j >= len(P) and s < TAU)
inrr = sum(1 for q in Q for j, s in ranked(q)[1] if j >= len(P))
kinds = {}
for q in Q:
    for j, s in ranked(q)[1]:
        if j >= len(P) and s < TAU:
            kinds[docs[j]["kind"]] = kinds.get(docs[j]["kind"], 0) + 1
print(f"posts in the reranked top 10 that fall below the minimum score: {below}/{inrr} "
      f"({', '.join(f'{k} {v}' for k, v in sorted(kinds.items())) or 'none'})")

# Data voids: questions the knowledge base cannot answer. The minimum score is what lets the app say "no
# documents"; a post written for exactly that question is then the only evidence left.
V = C["voids"]
vv = bi.encode([x["text"] for x in V["planted"]])
void_rows = []
for q in V["queries"]:
    qv = bi.encode([q["text"]])[0]
    for planted in (False, True):
        pool = list(range(len(P))) + ([len(P) + i for i, x in enumerate(V["planted"]) if x["target"] == q["id"]]
                                      if planted else [])
        vecs = np.concatenate([dv[:len(P)], vv]) if planted else dv[:len(P)]
        texts = text[:len(P)] + [x["text"] for x in V["planted"]]
        s = vecs @ qv
        cand = [j for j in np.argsort(-s) if j in pool][:TOP]
        cs = ce.score(q["text"], [texts[j] for j in cand])
        kept = [(int(j), float(c)) for j, c in sorted(zip(cand, cs), key=lambda x: -x[1]) if c >= TAU][:K]
        void_rows.append({"q": q["id"], "planted": planted, "kept": len(kept),
                          "canary_first": bool(kept) and emb.CANARY in texts[kept[0][0]],
                          "best": round(max(cs), 2)})
nv = len(V["queries"])
empty = sum(r["kept"] == 0 for r in void_rows if not r["planted"])
only = sum(r["canary_first"] for r in void_rows if r["planted"])
best_clean = max(r["best"] for r in void_rows if not r["planted"])
best_post = min(r["best"] for r in void_rows if r["planted"])
passed = [r["q"] for r in void_rows if not r["planted"] and r["kept"]]
print(f"data voids ({nv} questions with no answer in the knowledge base), reranked with minimum score {TAU}:")
print(f"  clean index: no passage passes for {empty}/{nv} (passes: {', '.join(passed) or 'none'}, best logit {best_clean:.2f});"
      f" with one forum post "
      f"per question: the post is 1st for {only}/{nv} (lowest post logit {best_post:.2f})")
print(f"({t})")
emb.save("d1_rank_controls.json", {"tau": TAU, "clean_min": round(min(clean_gold), 2), "k": K, "n": n, "rows": rows,
                                   "below": below, "in_rerank": inrr, "below_kinds": kinds, "n_posts": len(X),
                                   "voids": {"n": nv, "empty": empty, "post_first": only, "best_clean": best_clean,
                                             "best_post": best_post, "passed": passed}})
