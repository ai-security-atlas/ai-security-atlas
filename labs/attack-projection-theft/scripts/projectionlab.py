"""Shared pieces of LAB-37 (imported by the step scripts in this folder).

* The victim: SmolLM2-135M-Instruct at a pinned revision (the shared `tinylm` fixture), served as
  "lantern-mini-1", a fictional Lantern Labs API whose model card discloses nothing about the
  architecture. The `victim_api` fixture (LAB-09) serves classifier probability vectors; it has no
  endpoint for a language model's full logit rows, so this lab serves them from here instead — same
  rules, same shape: per-key policies, budgets, a JSONL query log.
* The API (Policy + make_app + Server): a FastAPI app on 127.0.0.1 inside the container. A Policy
  decides how much of each answer a caller sees: full next-token logprob rows (base64 float32),
  top-k only, rounding, noise, and whether `logit_bias` is accepted.
* The attack math (Carlini et al. 2024, "Stealing Part of a Production Language Model"):
  stack n answered rows, center them (this removes the per-row log-softmax constant), and the
  matrix has rank = the model's hidden size d. The singular-value spectrum drops off a cliff after
  d, so the hidden size falls out of the answers; the top-d right singular vectors then span the
  same subspace as the output projection, i.e. the projection is recovered up to an unknown
  invertible linear map. least-squares fit against the true lm_head (operator-side) measures it.
"""

import base64
import json
import socket
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import labkit

CANARY = "ATLAS-CANARY-svd7"          # tags every artifact this lab's attack writes
VICTIM_ID = "lantern-mini-1"          # fictional model name on the API's card
OWNER = "Lantern Labs (fictional company)"
PROMPT_SEED = 5                       # seed of the attacker's random-prompt stream
N_ROWS = 1200                         # rows the main attack collects (Step 2)
BATCH = 100                           # prompts per /v1/score request (the API's cap)
BIAS = 50.0                           # logit_bias used by the top-k escape (Step D1)
CLARITY = 10.0                        # a knee counts as clear only above this s[k-1]/s[k] ratio


# ---------------------------------------------------------------- victim model
def load_victim(download=False):
    """(tokenizer, model) for the pinned 135M victim, fp32, frozen."""
    import tinylm
    tok, model = tinylm.load("smollm2-135m", download)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = "<|im_end|>"
    return tok, model


def true_head(model):
    """The output projection as a float64 |V| x d matrix (lm_head; tied to the input embeddings)."""
    import numpy as np
    return model.lm_head.weight.detach().numpy().astype(np.float64)


def victim_card():
    return {"model": VICTIM_ID, "owned_by": OWNER,
            "serves": ["full next-token logprob rows", "top-k logprobs"],
            "architecture": "undisclosed", "parameters": "undisclosed",
            "max_prompts_per_request": BATCH}


# ---------------------------------------------------------------- the lab API
@dataclass
class Policy:
    detail: str = "full"              # full | topk — the most any caller can be served
    top_k: int = 5                    # entries per top-k answer
    allow_logit_bias: bool = True     # whether requests may bias chosen tokens
    round_digits: int = -1            # round every returned logprob (-1 = no rounding)
    noise: float = 0.0                # Gaussian noise added to every returned logprob
    budget: int | None = None         # prompts this key may send over the life of the log

    def name(self):
        s = self.detail
        if self.detail == "topk":
            s += str(self.top_k)
        if not self.allow_logit_bias:
            s += " no-bias"
        if self.round_digits >= 0:
            s += f" round={self.round_digits}"
        if self.noise > 0:
            s += f" noise={self.noise:g}"
        if self.budget is not None:
            s += f" budget={self.budget}"
        return s


def make_app(tok, model, keys, log_path=None):
    """The fictional lantern-mini-1 API. `keys` maps key -> Policy. Everything is logged."""
    import torch
    import numpy as np
    from fastapi import FastAPI, Header
    from fastapi.responses import JSONResponse

    app = FastAPI(title=f"victim-api lm ({VICTIM_ID})", docs_url=None, redoc_url=None, openapi_url=None)
    log_path = Path(log_path) if log_path else None
    used = {k: 0 for k in keys}
    served_rows = {k: 0 for k in keys}
    lock = threading.Lock()

    def write(row):
        if log_path:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")

    def usage(key):
        return {"key": key, "used": used[key], "budget": keys[key].budget,
                "remaining": None if keys[key].budget is None else keys[key].budget - used[key]}

    @app.get("/v1/model")
    def card():
        return victim_card()

    @app.get("/v1/usage")
    def get_usage(x_api_key: str = Header("")):
        if x_api_key not in keys:
            return JSONResponse({"error": "unknown API key"}, status_code=401)
        return usage(x_api_key)

    @app.post("/v1/score")
    def score(body: dict, x_api_key: str = Header("")):
        if x_api_key not in keys:
            return JSONResponse({"error": "unknown API key"}, status_code=401)
        pol = keys[x_api_key]
        prompts = list(body.get("prompts") or [])
        want = body.get("detail", pol.detail)
        bias = body.get("logit_bias") or {}
        n = len(prompts)
        row = {"t": round(time.time(), 3), "key": x_api_key, "n": n, "requested": want,
               "served": None, "status": 200, "tokens": 0}
        if not prompts or n > BATCH:
            row["status"] = 422
            write(row)
            return JSONResponse({"error": f"prompts must be a non-empty list of at most {BATCH} strings"}, status_code=422)
        if want == "full" and pol.detail != "full":
            row["status"] = 403
            write(row)
            return JSONResponse({"error": "full rows are not offered to this key", "usage": usage(x_api_key)}, status_code=403)
        if want not in ("full", "topk"):
            row["status"] = 422
            write(row)
            return JSONResponse({"error": "detail must be full or topk"}, status_code=422)
        if bias and not pol.allow_logit_bias:
            row["status"] = 400
            write(row)
            return JSONResponse({"error": "logit_bias is not accepted by this API", "usage": usage(x_api_key)}, status_code=400)
        with lock:
            if pol.budget is not None and used[x_api_key] + n > pol.budget:
                row["status"] = 429
                write(row)
                return JSONResponse({"error": "query budget exceeded", "usage": usage(x_api_key)}, status_code=429)
            used[x_api_key] += n
        k = max(1, min(int(body.get("top_k", pol.top_k)), pol.top_k))
        enc = tok(prompts, return_tensors="pt", padding=True)
        with torch.no_grad():
            logits = model(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"]).logits[:, -1].float()
        for t, b in bias.items():
            logits[:, int(t)] += float(b)
        lp = torch.log_softmax(logits, -1).cpu().numpy()
        if pol.noise > 0:
            g = np.random.default_rng(PROMPT_SEED + served_rows[x_api_key])
            lp = lp + g.normal(0.0, pol.noise, lp.shape).astype(lp.dtype)
            served_rows[x_api_key] += n
        if pol.round_digits >= 0:
            lp = np.round(lp, pol.round_digits)
        rows_out = []
        if want == "full":
            rows_out = [base64.b64encode(r.astype("f4").tobytes()).decode() for r in lp]
        else:
            for r in lp:
                top = np.argsort(-r, kind="stable")[:k]
                rows_out.append({"top": [{"id": int(i), "token": tok.decode([int(i)]),
                                          "logprob": float(r[i])} for i in top]})
        row.update(served=want, prompts=prompts, prompt_tokens=int(enc["attention_mask"].sum()))
        write(row)
        return {"model": VICTIM_ID, "detail": want, "rows": rows_out, "usage": usage(x_api_key)}

    app.state.usage = usage
    return app


class Server:
    """Serve make_app() on 127.0.0.1:<free port> in a background thread; .post() sends real HTTP."""

    def __init__(self, tok, model, keys, log_path=None, quiet=False):
        import httpx
        import uvicorn
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        self.keys = keys
        self.app = make_app(tok, model, keys, log_path)
        self.server = uvicorn.Server(uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="warning"))
        threading.Thread(target=self.server.run, daemon=True).start()
        while not self.server.started:
            time.sleep(0.05)
        self.url = f"http://127.0.0.1:{self.port}"
        self.http = httpx.Client(base_url=self.url, timeout=600)
        self.queries = 0
        if not quiet:
            names = ", ".join(f"{k} ({p.name()})" for k, p in keys.items())
            print(f"[note] victim API {self.url} (inside this container only) · keys: {names}", flush=True)

    def post(self, path, body, key):
        self.queries += 1
        r = self.http.post(path, json=body, headers={"X-API-Key": key})
        return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else {})

    def get(self, path, key=None):
        r = self.http.get(path, headers={"X-API-Key": key} if key else {})
        return r.status_code, r.json()

    def close(self):
        self.http.close()
        self.server.should_exit = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def read_log(path):
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------- attack math
def decode_row(b64):
    import numpy as np
    return np.frombuffer(base64.b64decode(b64), dtype=np.float32)


def centered(mat):
    import numpy as np
    m = mat.astype(np.float64)
    return m - m.mean(1, keepdims=True)      # removes the per-row log-softmax constant


def singular_values(mat):
    """Singular values, largest first, of the centered row stack (float64; n x n eigvalsh)."""
    import numpy as np
    m = centered(mat)
    return np.sqrt(np.clip(np.linalg.eigvalsh(m @ m.T)[::-1], 0, None))


def knee(s):
    """(k, ratio): the index after the spectrum's largest log-gap, and s[k-1]/s[k]."""
    import numpy as np
    gaps = np.log(s[:-2] / np.maximum(s[1:-1], 1e-300))
    k = int(gaps.argmax()) + 1
    return k, float(s[k - 1] / max(s[k], 1e-300))


def estimate_dim(mat, clarity=CLARITY):
    """The hidden-size read: (k, ratio, clear). clear is False when the gap is weak."""
    k, ratio = knee(singular_values(mat))
    return {"dim": k, "ratio": ratio, "clear": ratio >= clarity}


def recover_basis(mat, d):
    """The top-d right singular vectors of the centered rows: an orthonormal |V| x d basis whose
    span equals the (column-centered) output projection's span."""
    import numpy as np
    m = centered(mat)
    w = np.linalg.eigh(m @ m.T)
    lam = np.clip(w.eigenvalues[::-1][:d], 1e-300, None)
    u = w.eigenvectors[:, ::-1][:, :d]
    return ((m.T @ u) / np.sqrt(lam)).astype(np.float64)


def fit_basis(B, model):
    """Operator-side eval-fidelity check: how exactly the true lm_head fits inside span(B).

    The API answers are per-row centered, so the comparable object is the column-centered head
    Wc = W - mean(W). least squares gives A = B^T Wc; the relative residual and the smallest
    principal-angle cosine say how much of Wc is (not) inside the recovered span.
    """
    import numpy as np
    W = true_head(model)
    Wc = W - W.mean(0, keepdims=True)
    A = B.T @ Wc
    resid = np.linalg.norm(Wc - B @ A) / np.linalg.norm(Wc)
    Qr = np.linalg.qr(Wc)[0]
    cos_min = float(np.linalg.svd(B.T @ Qr, compute_uv=False).min())
    return {"rel_resid": float(resid), "cos_min": cos_min, "map_shape": list(A.shape)}


def random_prompts(tok, n, seed=PROMPT_SEED, length=6):
    """The attacker's token-soup prompts: n random token ids, decoded to text (seeded)."""
    import torch
    g = torch.Generator().manual_seed(seed)
    ids = torch.randint(0, len(tok), (n, length), generator=g)
    return [tok.decode(r, skip_special_tokens=True) for r in ids]


def natural_prompts(pool, n, seed=11):
    """Two random sentences from `pool` joined: natural-looking text, n distinct combos (seeded)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    out, seen = [], set()
    while len(out) < n:
        a, b = rng.choice(len(pool), 2, replace=False)
        if (a, b) in seen:
            continue
        seen.add((a, b))
        out.append(pool[a] + " " + pool[b])
    return out


def score_prompts(model, tok, texts):
    """Mean per-token logprob of each text under the victim (the D3 monitor's randomness score)."""
    import numpy as np
    import torch
    out = []
    for t in texts:
        enc = tok(t, return_tensors="pt")
        ids = enc["input_ids"][0]
        with torch.no_grad():
            lp = torch.log_softmax(model(enc["input_ids"]).logits[0].float(), -1)
        tgt = ids[1:]
        out.append(float(lp[torch.arange(len(tgt)), tgt].mean()))
    return out


def load_prompt_pool():
    """The bundled sentence pool + honest user prompts (assets/prompts.json)."""
    data = json.loads(labkit.inp("assets/prompts.json").read_text(encoding="utf-8"))
    return data["pool"], data["honest"]


def save(name, obj):
    import numpy as np
    p = labkit.out(name)
    if isinstance(obj, np.ndarray):
        np.save(p, obj)
        return p
    p.write_text(json.dumps(obj, indent=1, default=lambda o: asdict(o)) + "\n", encoding="utf-8")
    return p
