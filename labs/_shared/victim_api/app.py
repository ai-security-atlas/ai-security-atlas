"""The victim-api FastAPI app (see the package docstring)."""

import hashlib
import json
import math
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

DETAILS = ("label", "topk", "probs", "logprobs")   # least to most detail
TOPK_CAP = 5


@dataclass
class KeyPolicy:
    budget: Optional[int] = None          # input rows this key may send in total; None = unlimited
    max_detail: str = "logprobs"          # the most detail this key is served
    round_digits: Optional[int] = None    # round probabilities to this many decimals


@dataclass
class Watermark:
    secret: str                           # the owner's key for selecting watermarked inputs
    rate: float = 0.02                    # fraction of inputs answered with a watermark label
    decimals: int = 4                     # inputs are rounded before hashing

    def pick(self, x):
        """Return the watermark class for input x, or None if x is not selected."""
        h = hashlib.sha256(self.secret.encode() + np.round(np.asarray(x, dtype=np.float64), self.decimals).tobytes()).digest()
        if int.from_bytes(h[:4], "big") / 2 ** 32 >= self.rate:
            return None
        return h[4]  # turned into a class != top class by the caller


class PredictRequest(BaseModel):
    inputs: List[List[float]]
    detail: str = "label"
    k: int = 3


def read_log(path):
    """Every JSON line of a query log (empty list if the file does not exist)."""
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def _r(v, digits):
    return float(v) if digits is None else round(float(v), digits)


def create_app(predict_proba: Callable, classes, n_features: int, keys: dict, log_path=None,
               model_id: str = "victim", watermark: Optional[Watermark] = None, log_inputs: bool = True):
    classes = [str(c) for c in classes]
    C = len(classes)
    log_path = Path(log_path) if log_path else None
    wm_path = log_path.with_suffix(".wm.jsonl") if log_path else None
    used = {k: 0 for k in keys}
    for row in read_log(log_path) if log_path else []:     # budgets survive a restart
        if row.get("status") == 200 and row.get("key") in used:
            used[row["key"]] += row["n"]
    lock = threading.Lock()
    app = FastAPI(title=f"victim-api ({model_id})", docs_url=None, redoc_url=None, openapi_url=None)

    def write(path, row):
        if path:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")

    def usage(key):
        b = keys[key].budget
        return {"used": used[key], "budget": b, "remaining": None if b is None else b - used[key]}

    def unknown():
        return JSONResponse({"error": "unknown API key"}, status_code=401)

    @app.get("/v1/model")
    def model():
        return {"model": model_id, "classes": classes, "n_features": n_features, "details": list(DETAILS)}

    @app.get("/v1/usage")
    def get_usage(x_api_key: str = Header("")):
        if x_api_key not in keys:
            return unknown()
        return {"key": x_api_key, **usage(x_api_key)}

    @app.post("/v1/predict")
    def predict(req: PredictRequest, x_api_key: str = Header("")):
        if x_api_key not in keys:
            return unknown()
        pol = keys[x_api_key]
        if req.detail not in DETAILS:
            return JSONResponse({"error": f"detail must be one of {list(DETAILS)}"}, status_code=422)
        X = np.asarray(req.inputs, dtype=np.float64)
        if X.ndim != 2 or X.shape[1] != n_features or len(X) == 0:
            return JSONResponse({"error": f"inputs must be a non-empty list of {n_features}-number rows"}, status_code=422)
        served = DETAILS[min(DETAILS.index(req.detail), DETAILS.index(pol.max_detail))]
        n = len(X)
        with lock:
            if pol.budget is not None and used[x_api_key] + n > pol.budget:
                write(log_path, {"t": round(time.time(), 3), "key": x_api_key, "n": n, "requested": req.detail,
                                 "served": None, "status": 429})
                return JSONResponse({"error": "query budget exceeded", "usage": usage(x_api_key)}, status_code=429)
            used[x_api_key] += n
        P = np.asarray(predict_proba(X), dtype=np.float64)
        top = P.argmax(1)
        for i in range(n) if watermark else []:
            b = watermark.pick(X[i])
            if b is not None:
                w = (top[i] + 1 + b % (C - 1)) % C              # any class but the true top one
                P[i, [top[i], w]] = P[i, [w, top[i]]]
                top[i] = w
                write(wm_path, {"key": x_api_key, "input": X[i].tolist(), "label": classes[w]})
        k = max(1, min(req.k, TOPK_CAP, C))
        results = []
        for i in range(n):
            p = P[i]
            r = {"label": classes[top[i]]}
            if served == "topk":
                order = np.argsort(-p, kind="stable")[:k]
                r["top_k"] = [{"label": classes[j], "p": _r(p[j], pol.round_digits)} for j in order]
            elif served == "probs":
                r["probs"] = [_r(v, pol.round_digits) for v in p]
            elif served == "logprobs":
                q = [_r(v, pol.round_digits) for v in p]
                r["logprobs"] = [math.log(v) if v > 0 else None for v in q]
            results.append(r)
        row = {"t": round(time.time(), 3), "key": x_api_key, "n": n, "requested": req.detail, "served": served,
               "status": 200, "labels": [r["label"] for r in results], "top_p": [round(float(v), 4) for v in P.max(1)]}
        if log_inputs:
            row["inputs"] = X.tolist()
        write(log_path, row)
        return {"model": model_id, "detail": served, "results": results, "usage": usage(x_api_key)}

    return app
