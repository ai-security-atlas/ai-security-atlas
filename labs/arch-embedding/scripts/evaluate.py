"""Evaluate: re-measure the lab's claims and compare with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python arch-embedding/scripts/evaluate.py
Counts are graded none (0), some (under half), most (half or more) and all, so small CPU-to-CPU drift does
not flip a row. Needs atlas-app running (Setup 2). Ends with exactly "RESULT: REPRODUCED" or
"RESULT: MISMATCH (<what differed>)".
"""
import json

import numpy as np

import labkit

labkit.banner()

import emb  # noqa: E402


def grade(k, n):
    return "none" if k == 0 else "all" if k == n else "most" if 2 * k >= n else "some"


TOP, K = 10, 4
t = emb.Timer()
bi, ce = emb.BiEncoder(), emb.CrossEncoder()
C = emb.corpus()
P, Q, X = C["passages"], C["queries"], C["planted"]
pv = bi.encode([p["text"] for p in P])
qv = bi.encode([q["text"] for q in Q])
ids = [p["id"] for p in P]
got, raw = {}, {}
n = len(Q)

k = sum(int(np.argmax(pv @ v)) == ids.index(q["gold"]) for q, v in zip(Q, qv))
raw["clean: gold 1st by cosine"] = (int(k), n)
got["clean index · gold passage 1st"] = grade(k, n)

emb.app_wait()
av = np.array(emb.app_post("/admin/rag/embed", {"texts": [q["text"] for q in Q]})["vectors"], dtype=np.float32)
agree = float((av * qv).sum(1).min())
raw["atlas-app vs torch: min cosine"] = (round(agree, 6),)
got["atlas-app ONNX vectors = torch vectors"] = "same" if agree > 0.9999 else "differ"

xv = dict(zip([x["id"] for x in X], bi.encode([x["text"] for x in X])))
for kind in ("mirror", "stuffed"):
    c1 = r1 = k4 = 0
    for q, v in zip(Q, qv):
        x = next(x for x in X if x["target"] == q["id"] and x["kind"] == kind)
        s = np.append(pv @ v, xv[x["id"]] @ v)
        order = list(np.argsort(-s))
        cand = order[:TOP]
        texts = [p["text"] for p in P] + [x["text"]]
        cs = ce.score(q["text"], [texts[j] for j in cand])
        rer = [cand[j] for j in np.argsort(-np.array(cs))]
        c1 += order[0] == len(P)
        r1 += rer[0] == len(P)
        k4 += len(P) in rer[:K]
    raw[f"{kind}: 1st cos / 1st rerank / top 4 rerank"] = (int(c1), int(r1), int(k4), n)
    if kind == "mirror":   # stuffed posts sit at exactly half (6/12) by cosine, too close to a grade boundary
        got[f"{kind} post · 1st by cosine"] = grade(c1, n)
    got[f"{kind} post · 1st after rerank"] = grade(r1, n)
    got[f"{kind} post · in top 4 after rerank"] = grade(k4, n)

hits = [emb.app_post("/admin/rag/search", {"collection": emb.PLANTED, "query": q["text"], "k": K})["hits"] for q in Q]
a4 = sum(any(emb.CANARY in h["text"] for h in hs) for hs in hits)
raw["atlas-app planted index: canary in top 4"] = (int(a4), n)
got["atlas-app index · canary in top 4"] = grade(a4, n)

notes = emb.notes()
leaked = bi.encode([x[2] for x in notes])
for key, guess in (("A", False), ("B", True)):
    cand = emb.candidates(guess)
    cv = bi.encode([c[1] for c in cand], bs=128)
    r = sum(g[0] == x[1] for g, x in zip(emb.recover(leaked, cv, [c[0] for c in cand]), notes))
    raw[f"inversion attacker {key}: notes recovered"] = (int(r), len(notes), len(cand))
    got[f"inversion · attacker {key} whole note"] = grade(r, len(notes))
    if key == "A":
        cvA, fA = cv, [c[0] for c in cand]

R = np.linalg.qr(np.random.default_rng(20261101).standard_normal((384, 384)))[0].astype(np.float32)
rot = leaked @ R
blind = sum(g[0] == x[1] for g, x in zip(emb.recover(rot, cvA, fA), notes))
idx = np.random.default_rng(5).choice(len(fA), 64, replace=False)
U, _, Vt = np.linalg.svd(cvA[idx].T @ (cvA[idx] @ R))
undone = sum(g[0] == x[1] for g, x in zip(emb.recover(rot @ (U @ Vt).T, cvA, fA), notes))
raw["rotation: blind / with 64 planted notes"] = (int(blind), int(undone), len(notes))
got["rotation · blind attacker"] = grade(blind, len(notes))
got["rotation · attacker with 64 planted notes"] = grade(undone, len(notes))

# D1: all 36 posts in the index, one author; per-author cap 1 after rerank, versus an atlas-kb allowlist.
allv = np.concatenate([pv, np.array([xv[x["id"]] for x in X])])
texts = [p["text"] for p in P] + [x["text"] for x in X]
capped = allow = 0
for q, v in zip(Q, qv):
    cand = list(np.argsort(-(allv @ v))[:TOP])
    cs = ce.score(q["text"], [texts[j] for j in cand])
    rer = [cand[j] for j in np.argsort(-np.array(cs))]
    ctx, post = [], 0
    for j in rer:
        if j >= len(P):
            if post:
                continue
            post += 1
        ctx.append(j)
    capped += any(emb.CANARY in texts[j] for j in ctx[:K])
    allow += any(emb.CANARY in texts[j] for j in [j for j in rer if j < len(P)][:K])
raw["D1 canary in top 4: 1 post per author / atlas-kb only"] = (int(capped), int(allow), n)
got["D1 · 1 post per author: canary in top 4"] = grade(capped, n)
got["D1 · atlas-kb only: canary in top 4"] = grade(allow, n)

for k_, v in raw.items():
    print(f"  measured {k_}: {v}")
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
print(f"{'condition':<44} {'expected':<10} got")
for cond, want in expected.items():
    print(f"{cond:<44} {str(want):<10} {got.get(cond)}")
emb.save("evaluate.json", {"got": got, "raw": {k_: list(v) for k_, v in raw.items()}})
diff = [c for c, want in expected.items() if got.get(c) != want]
print(f"({t})")
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
