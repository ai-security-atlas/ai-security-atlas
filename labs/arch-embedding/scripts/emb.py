"""Shared helpers for LAB-40 arch-embedding: pinned models, the fixture corpus and the atlas-app client.

Two small open models, both pinned to one revision and run on CPU in the workbench with plain transformers
(sentence-transformers is not in the workbench image; the code below does what it does for these two models):
  * the bi-encoder: sentence-transformers/all-MiniLM-L6-v2. Each text is encoded on its own, the token
    vectors are mean-pooled over the attention mask and L2-normalized; relevance is the cosine of two vectors.
  * the cross-encoder: cross-encoder/ms-marco-MiniLM-L6-v2. The query and one passage are read together as
    one input ([CLS] query [SEP] passage [SEP]) and a linear head returns one relevance logit.
atlas-app (labs/_shared/atlas_app, profile rag-agent) runs the same bi-encoder as chromadb's ONNX model; this
lab's atlas_profiles.py loads assets/corpus.json into two collections there. Every product, person and
record is fictional; planted passages and leaked records carry only the inert canary ATLAS-CANARY-3mbd.
"""
import json
import os
import time
import urllib.error
import urllib.request

import labkit

from transformers.utils import logging as _tl  # noqa: E402

_tl.set_verbosity_error()

CANARY = "ATLAS-CANARY-3mbd"
THREADS = int(os.environ.get("TINYLM_THREADS", "4"))
BI = ("sentence-transformers/all-MiniLM-L6-v2", "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
      ["config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt",
       "model.safetensors", "modules.json", "sentence_bert_config.json", "1_Pooling/config.json"])
CROSS = ("cross-encoder/ms-marco-MiniLM-L6-v2", "233902d25c440f23af6f7d6e94d2946bac0bee0a",
         ["config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt",
          "model.safetensors"])
URL = os.environ.get("ATLAS_APP_URL", "http://atlas-app:8000").rstrip("/")
CLEAN, PLANTED = "archemb-kb", "archemb-planted"   # the plug-in's two collections in atlas-app


def torch():
    import torch as t
    t.set_num_threads(THREADS)
    return t


def fetch(spec):
    from huggingface_hub import snapshot_download
    repo, rev, files = spec
    return snapshot_download(repo, revision=rev, allow_patterns=files)


class BiEncoder:
    """all-MiniLM-L6-v2 as sentence-transformers runs it: mean pooling, then L2 normalization."""

    def __init__(self):
        import transformers
        self.t = torch()
        path = fetch(BI)
        self.tok = transformers.AutoTokenizer.from_pretrained(path)
        self.model = transformers.AutoModel.from_pretrained(path).train(False)
        self.max_len = json.load(open(os.path.join(path, "sentence_bert_config.json")))["max_seq_length"]
        self.pooling = json.load(open(os.path.join(path, "1_Pooling", "config.json")))

    def encode(self, texts, bs=32):
        """Unit-length vectors, one row per text (numpy float32)."""
        import numpy as np
        out = []
        with self.t.no_grad():
            for i in range(0, len(texts), bs):
                enc = self.tok(list(texts[i:i + bs]), return_tensors="pt", padding=True, truncation=True,
                               max_length=self.max_len)
                h = self.model(**enc).last_hidden_state
                m = enc["attention_mask"].unsqueeze(-1).float()
                v = (h * m).sum(1) / m.sum(1).clamp(min=1e-9)
                out.append(self.t.nn.functional.normalize(v, dim=-1).numpy())
        return np.concatenate(out).astype(np.float32)


class CrossEncoder:
    """ms-marco-MiniLM-L6-v2: one forward pass per (query, passage) pair, one logit out."""

    def __init__(self):
        import transformers
        self.t = torch()
        path = fetch(CROSS)
        self.tok = transformers.AutoTokenizer.from_pretrained(path)
        self.model = transformers.AutoModelForSequenceClassification.from_pretrained(path).train(False)

    def score(self, query, passages, bs=32):
        out = []
        with self.t.no_grad():
            for i in range(0, len(passages), bs):
                chunk = list(passages[i:i + bs])
                enc = self.tok([query] * len(chunk), chunk, return_tensors="pt", padding=True, truncation=True,
                               max_length=512)
                out += self.model(**enc).logits[:, 0].tolist()
        return out


def params_m(model):
    return round(sum(p.numel() for p in model.parameters()) / 1e6, 1)


# ---------------------------------------------------------------- fixture
def corpus():
    return json.loads(labkit.inp("assets/corpus.json").read_text())


def short(s, n=48):
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n - 3] + "..."


def rank_of(order_ids, pid):
    """1-based rank of pid in a ranked id list (None if absent)."""
    return order_ids.index(pid) + 1 if pid in order_ids else None


# ---------------------------------------------------------------- work/ files
def save(name, obj):
    labkit.out(name).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def read(name, step):
    p = labkit.work() / name
    if not p.exists():
        raise SystemExit(f"[!!] {p} is missing; run {step} first")
    return json.loads(p.read_text())


class Timer:
    def __init__(self):
        self.t0 = time.time()

    def __str__(self):
        return f"{time.time() - self.t0:.0f}s"


# ---------------------------------------------------------------- atlas-app client
def _req(method, path, body=None, key=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if key:
        h["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(URL + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:300]}


def app_get(path):
    code, body = _req("GET", path)
    if code != 200:
        raise SystemExit(f"[!!] atlas-app HTTP {code} on {path}: {body}")
    return body


def app_post(path, body, key=None):
    code, out = _req("POST", path, body, key)
    if code != 200:
        raise SystemExit(f"[!!] atlas-app HTTP {code} on {path}: {out}")
    return out


def app_wait(timeout=180):
    """Wait until atlas-app answers /healthz and its RAG index is built. Returns the /admin/rag body."""
    t0 = time.time()
    while True:
        try:
            r = app_get("/admin/rag")
            if r.get("ready"):
                return r
            if r.get("error"):
                raise SystemExit(f"[!!] atlas-app RAG index failed: {r['error']}")
        except (urllib.error.URLError, OSError, SystemExit) as e:
            if isinstance(e, SystemExit) and "failed" in str(e):
                raise
            if time.time() - t0 > timeout:
                raise SystemExit(f"[!!] atlas-app not reachable at {URL} ({e}); start it (Setup 2)")
        time.sleep(2)


# ---------------------------------------------------------------- Step 6 / D2: support notes and their vectors
NAMES = ["Dana Okafor", "Luis Romero", "Mei Tanaka", "Priya Nair", "Tom Becker", "Ana Silva", "Omar Haddad",
         "Grace Kim", "Ivan Petrov", "Sara Lind", "Jonas Weber", "Leila Ahmadi", "Noah Grant", "Ruth Mensah",
         "Kenji Mori", "Elena Costa"]
MORE_NAMES = ["Alex Turner", "Bea Novak", "Carl Jensen", "Dina Rossi", "Emil Larsen", "Fatma Yilmaz", "Gus Moreno",
              "Hana Sato", "Ian Doyle", "Jade Wu", "Karl Brandt", "Lina Haddad", "Marco Bianchi", "Nia Owusu",
              "Oscar Diaz", "Pia Berg"]   # names the attacker also tries; no stored note uses them
CITIES = ["Tacoma", "Boise", "Fresno", "Halifax", "Spokane", "Eugene", "Reno", "Victoria", "Salem", "Yakima"]
PRODUCTS = ["Orbit desk lamp", "Cable dock", "Pebble speaker", "Drift fan", "Slate keyboard", "Halo webcam"]
ISSUES = ["it stopped charging", "they asked for a refund", "the case arrived cracked", "they want to cancel the order",
          "the delivery was two weeks late"]
ISSUES_GUESS = ["not charging", "refund request", "cracked case", "order cancellation", "late delivery"]
NOTE = "Support note: {n} from {c} called about the {p}; {i}."     # how the shop writes its notes
GUESS = "{n} ({c}) - {p} - {i}"                                     # the attacker's own wording
N_NOTES, CANARY_ROW = 40, 17


def notes():
    """The 40 stored support notes: [(row id, (name, city, product, issue) indexes, text)]. Row 17 is the
    canary record: its id is ATLAS-CANARY-3mbd."""
    import itertools
    import numpy as np
    combos = list(itertools.product(range(len(NAMES)), range(len(CITIES)), range(len(PRODUCTS)), range(len(ISSUES))))
    pick = np.random.default_rng(7).choice(len(combos), N_NOTES, replace=False)
    out = []
    for r, i in enumerate(pick):
        a, b, c, d = combos[i]
        rid = CANARY if r == CANARY_ROW else f"note-{r:03d}"
        out.append((rid, (a, b, c, d), NOTE.format(n=NAMES[a], c=CITIES[b], p=PRODUCTS[c], i=ISSUES[d])))
    return out


def candidates(guess=False):
    """Every combination the attacker can write: [(fields, text)]. guess=True: 32 names and the attacker's
    own wording (GUESS, ISSUES_GUESS); False: the shop's 16 names and exact template."""
    import itertools
    names = NAMES + MORE_NAMES if guess else NAMES
    tmpl, issues = (GUESS, ISSUES_GUESS) if guess else (NOTE, ISSUES)
    return [((a, b, c, d), tmpl.format(n=names[a], c=CITIES[b], p=PRODUCTS[c], i=issues[d]))
            for a, b, c, d in itertools.product(range(len(names)), range(len(CITIES)), range(len(PRODUCTS)),
                                                range(len(issues)))]


def recover(leaked, cand_vecs, cand_fields):
    """Nearest candidate for each leaked vector: (fields, cosine, margin over the runner-up)."""
    import numpy as np
    S = leaked @ cand_vecs.T
    top2 = np.argsort(-S, axis=1)[:, :2]
    return [(cand_fields[i], float(S[r, i]), float(S[r, i] - S[r, j])) for r, (i, j) in enumerate(top2)]
