"""Step D2: treat stored vectors as sensitive data. Run from labs/:
    docker compose run --rm workbench python arch-embedding/scripts/d2_vectors.py
Part 1, a forensic check you can run on any RAG service: which routes hand out raw vectors, and to whom?
It calls atlas-app's routes with no credentials and looks for 384-number arrays in the answers.
Part 2, a control people reach for instead of access control: store every vector multiplied by a secret
random rotation (an orthogonal 384 x 384 matrix). Cosine similarity, and so retrieval, is unchanged, and the
Step 6 candidate search stops working. Then the attacker plants m notes of their own (they can write to the
store, as in Step 3), reads their rotated vectors in the same leak, and solves for the rotation (orthogonal
Procrustes, one SVD). Writes work/d2_vectors.json.
"""
import numpy as np

import labkit

labkit.banner()

import emb  # noqa: E402

t = emb.Timer()


def vectors_in(obj, dims=384):
    """Number of float arrays of length `dims` anywhere in a JSON value."""
    if isinstance(obj, list):
        if len(obj) == dims and all(isinstance(x, float) for x in obj):
            return 1
        return sum(vectors_in(x, dims) for x in obj)
    if isinstance(obj, dict):
        return sum(vectors_in(v, dims) for v in obj.values())
    return 0


# ---- part 1: who gets raw vectors?
emb.app_wait()
probe = []
q = emb.corpus()["queries"][0]["text"]
for method, path, body in (("POST", "/admin/rag/embed", {"texts": [q]}),
                           ("POST", "/admin/rag/search", {"collection": emb.CLEAN, "query": q, "k": 4}),
                           ("GET", f"/admin/rag/docs?collection={emb.CLEAN}", None),
                           ("GET", "/healthz", None)):
    code, out = emb._req(method, path, body)
    probe.append({"route": f"{method} {path.split('?')[0]}", "status": code, "vectors": vectors_in(out)})
print("part 1: atlas-app routes called with no API key")
print(f"  {'route':<24} {'HTTP':>4} {'384-d vectors in answer':>24}")
for p in probe:
    flag = "  <- raw vectors to anyone who can reach the port" if p["vectors"] and p["status"] == 200 else ""
    print(f"  {p['route']:<24} {p['status']:>4} {p['vectors']:>24}{flag}")

# ---- part 2: a secret rotation, and how a corpus writer undoes it
bi = emb.BiEncoder()
notes = emb.notes()
stored = bi.encode([n[2] for n in notes])
cand = emb.candidates(False)
cv = bi.encode([c[1] for c in cand], bs=128)
fields = [c[0] for c in cand]
R = np.linalg.qr(np.random.default_rng(20261101).standard_normal((384, 384)))[0].astype(np.float32)  # the secret
rot = stored @ R
C = emb.corpus()
P, Q = C["passages"], C["queries"]
pv, qv = bi.encode([p["text"] for p in P]), bi.encode([x["text"] for x in Q])
S0, S1 = qv @ pv.T, (qv @ R) @ (pv @ R).T
same = sum(list(np.argsort(-a)) == list(np.argsort(-b)) for a, b in zip(S0, S1))
print(f"part 2: stored vectors multiplied by a secret 384 x 384 rotation")
print(f"  retrieval: max |cosine change| {np.abs(S0 - S1).max():.1e}; identical ranking of all {len(P)} passages for "
      f"{same}/{len(Q)} questions")


def hits(vecs):
    return sum(g[0] == n[1] for g, n in zip(emb.recover(vecs, cv, fields), notes))


raw, blind = hits(stored), hits(rot)
rows = []
rng = np.random.default_rng(5)
print(f"  {'setting':<44} {'notes recovered':>15}")
print(f"  {'no rotation (Step 6, attacker A)':<44} {raw:>12}/{len(notes)}")
print(f"  {'rotated vectors only':<44} {blind:>12}/{len(notes)}")
for m in (4, 8, 16, 32, 64, 128):
    idx = rng.choice(len(cand), m, replace=False)          # m notes the attacker wrote into the store
    X, Y = cv[idx], cv[idx] @ R                              # their public-model vectors and leaked rotated ones
    U, _, Vt = np.linalg.svd(X.T @ Y)
    undo = rot @ (U @ Vt).T
    k = hits(undo)
    rows.append({"m": m, "recovered": k, "rel_err": float(np.linalg.norm(U @ Vt - R) / np.linalg.norm(R))})
    print(f"  {'rotated + ' + str(m) + ' notes they planted':<44} {k:>12}/{len(notes)}")
need = next((r["m"] for r in rows if r["recovered"] == len(notes)), None)
# How much of the secret do the planted notes pin down? Procrustes fits R only on the span of the planted vectors;
# that is enough when the stored notes live in nearly the same low-dimensional subspace.
sv = np.linalg.svd(cv - cv.mean(0), compute_uv=False) ** 2
dim99 = int(np.searchsorted(np.cumsum(sv) / sv.sum(), 0.99) + 1)
fit = next(r for r in rows if r["m"] == (need or 128))
rel = fit.pop("rel_err")
for r in rows:
    r.pop("rel_err", None)
print(f"  {len(cand)} candidate notes: {dim99} of 384 directions hold 99% of their variance; the rotation fitted from "
      f"{fit['m']} planted notes differs from the secret by {rel:.0%} (relative Frobenius norm) and recovers "
      f"{fit['recovered']}/{len(notes)} notes")
keeps = same == len(Q)
verdict = [f"the rotation {'keeps' if keeps else 'changes'} retrieval ({same}/{len(Q)} rankings identical)",
           f"blind recovery {blind}/{len(notes)}" + (" (stopped)" if blind == 0 else ""),
           f"{need} planted notes undo it for every note" if need else "no tested number of planted notes undid it for every note"]
print("; ".join(verdict))
print(f"({t})")
emb.save("d2_vectors.json", {"probe": probe, "same": int(same), "nq": len(Q), "raw": raw, "blind": blind,
                             "rows": rows, "need": need, "n": len(notes), "dim99": dim99, "rel_err": round(rel, 3)})
