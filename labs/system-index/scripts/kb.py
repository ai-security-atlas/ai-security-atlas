"""Client helpers for LAB-41 (imported by the step scripts; not run directly).

Scripts run in the workbench and reach atlas-app on the compose network at http://atlas-app:8000 (override
with ATLAS_APP_URL). They only use the operator stage views, so no model is called:
  /admin/rag/search   ranked chunks of a collection (chromadb, cosine distance = 1 - cosine similarity)
  /admin/rag/chunk    atlas-app's sentence-aware chunker at any size/overlap
  /admin/rag/embed    atlas-app's embedder (all-MiniLM-L6-v2, 384-d unit vectors)
  /admin/rag/preview  the exact messages a RAG profile would send to the model
The dropper's pages are the files of assets/drop/ (their names are the ground truth for "one writer").
"""
import json
import os
import time
import urllib.error
import urllib.request

import labkit
import numpy as np

import ingest

URL = os.environ.get("ATLAS_APP_URL", "http://atlas-app:8000").rstrip("/")
K = 4
OPEN, SIGNED = "sysidx-open", "sysidx-signed"
CANARY = ingest.CANARY
DROPPER = sorted(p.stem for p in ingest.DROPS.glob("*.md"))
FIRST_DROP = "refund-approvals-2026"
RULE = "refund up to $500"          # the handbook's refund rule (chunk refunds#0 holds it with its caveat)
CAVEAT = "orders paid by invoice"


def _req(method, path, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(URL + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"[!!] atlas-app HTTP {e.code} on {path}: {e.read().decode()[:300]}")


def get(path):
    return _req("GET", path)


def post(path, body=None):
    return _req("POST", path, body or {})


def wait_ready(quiet=False, timeout=120):
    """Wait until atlas-app answers and its index is built (after `docker compose restart atlas-app`)."""
    t0, err = time.time(), None
    while time.time() - t0 < timeout:
        try:
            h = get("/healthz")
            if h.get("rag", {}).get("ready") and "system-index" in (h.get("plugins") or {}):
                if not quiet:
                    print(f"[note] atlas-app index ready ({h['rag']['collections'].get(OPEN)} chunks in {OPEN}, "
                          f"{h['rag']['collections'].get(SIGNED)} in {SIGNED})", flush=True)
                return h
            err = h.get("rag", {}).get("error") or "plug-in system-index not loaded"
        except (OSError, SystemExit) as e:
            err = e
        time.sleep(1)
    raise SystemExit(f"[!!] atlas-app not ready at {URL} ({err}); did `docker compose up -d atlas-app` start it?")


def queries():
    return json.loads(labkit.inp("assets/queries.json").read_text())


def search(coll, q, k=K):
    return post("/admin/rag/search", {"collection": coll, "query": q, "principal": "atlas-staff", "k": k,
                                      "acl": "none"})["hits"]


def is_drop(h):
    return h["doc_id"] in DROPPER


def claimed(h):
    """The self-declared author that open ingestion copied into the source field."""
    s = h.get("source", "")
    return s.split("author: ", 1)[1].split(",")[0] if "author: " in s else ""


def embed(texts):
    return np.array(post("/admin/rag/embed", {"texts": list(texts)})["vectors"])


def handbook():
    return [d for d in ingest.folder() if d["rel"].startswith("handbook/")]


def chunk_config(cfg):
    """[(doc name, chunk text)] for the handbook under one chunker: (size, overlap) or "section" (D3)."""
    out = []
    for d in handbook():
        if cfg == "section":
            out += [(d["name"], t) for t in ingest.section_chunks(d)]
        else:
            size, overlap = cfg
            out += [(d["name"], c["text"]) for c in post("/admin/rag/chunk", {"text": d["body"], "size": size,
                                                                            "overlap": overlap})["chunks"]]
    return out


def caveat_table(cfg, k=K):
    """Re-index the handbook with one chunker and ask the five rule/caveat questions. Exact cosine search over
    atlas-app's embeddings (what chromadb approximates). Per question: rule in top k, caveat in top k, both in
    one chunk, and the caveat's rank."""
    chunks = chunk_config(cfg)
    V = embed(t for _, t in chunks)
    qs = queries()["caveats"]
    Q = embed(q["q"] for q in qs)
    heads = {}
    for d in handbook():
        for sec in d["body"].split("\n## ")[1:]:
            for q in qs:
                if q["caveat"] in sec:
                    heads[q["id"]] = sec.splitlines()[0].strip()
    rows = []
    for q, qv in zip(qs, Q):
        order = np.argsort(-(V @ qv))
        texts = [chunks[i][1] for i in order]
        top = texts[:k]
        cav = next(t for t in texts if q["caveat"] in t)
        rows.append({"id": q["id"], "rule": any(q["rule"] in t for t in top),
                     "caveat": any(q["caveat"] in t for t in top),
                     "together": any(q["rule"] in t and q["caveat"] in t for t in top),
                     "caveat_rank": next(i + 1 for i, t in enumerate(texts) if q["caveat"] in t),
                     "caveat_heading": heads[q["id"]] in cav, "heading": heads[q["id"]],
                     "top": [{"doc": chunks[i][0], "text": chunks[i][1], "sim": round(float(V[i] @ qv), 4)}
                             for i in order[:k]]})
    sizes = [len(t) for _, t in chunks]
    return {"config": cfg if cfg == "section" else f"{cfg[0]}/{cfg[1]}", "chunks": len(chunks),
            "mean_chars": round(sum(sizes) / len(sizes)), "rows": rows}


def save(name, obj):
    labkit.out(name).write_text(json.dumps(obj, indent=1))


def load(name):
    p = labkit.work() / name
    return json.loads(p.read_text()) if p.exists() else None


def short(s, n=60):
    s = " ".join((s or "").split())
    return repr(s if len(s) <= n else s[:n - 1] + "…")
