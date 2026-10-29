"""victim-api: a mock model-prediction API for the theft and privacy labs (`import victim_api`).

Founded by LAB-09 attack-model-imitation. PYTHONPATH=/labs/_shared is set on the workbench and
sandbox services, so any lab script can `import victim_api`. FastAPI + uvicorn + httpx, all in
the workbench v2 image. Nothing here listens on anything but 127.0.0.1 inside the container.

What it serves. Any classifier given as a function `predict_proba(X: ndarray[n, d]) -> ndarray[n, C]`
(rows sum to 1). The lab owns the model; the fixture only decides how much of each answer a
caller sees, counts and logs every query, and optionally watermarks answers.

    from victim_api import KeyPolicy, Watermark, create_app, serve, VictimClient
    app = create_app(predict_proba, classes=[str(i) for i in range(10)], n_features=64,
                     keys={"alice": KeyPolicy(budget=500), "thief": KeyPolicy(max_detail="label")},
                     log_path=labkit.out("queries.jsonl"))
    with serve(app) as url:                    # uvicorn in a background thread, 127.0.0.1:<free port>
        c = VictimClient(url, "alice")
        r = c.predict(X[:5], detail="probs")    # {"model", "detail", "results": [...], "usage": {...}}

Response detail (`detail`, least to most): DETAILS = ("label", "topk", "probs", "logprobs").
    label     {"label": "7"}
    topk      {"label": "7", "top_k": [{"label": "7", "p": 0.93}, ...]}      (k from the request, capped)
    probs     {"label": "7", "probs": [p0, ..., pC-1]}
    logprobs  {"label": "7", "logprobs": [log p0, ...]}
A key's KeyPolicy.max_detail caps what it gets (a "probs" request from a label-only key is served
as "label"; the response says which detail was served). KeyPolicy.round_digits rounds every
probability (and the probabilities behind logprobs; a probability rounded to 0 is sent as -inf in
logprobs, encoded as null in JSON).

Budgets. KeyPolicy.budget is the number of input rows (queries) a key may send over the life of
the log: a request that would go over it is refused whole with HTTP 429 and nothing is answered.
Usage is restored from `log_path` on start-up, so a budget survives a server restart.
Unknown keys get HTTP 401.

Log. One JSON line per request in `log_path`: t, key, n, requested and served detail, status,
the served labels, the top probability of each row and (log_inputs=True) the inputs themselves.
`read_log(path)` returns the lines; labs build monitors on it.

Watermark (DAWN-style, Szyller et al.): Watermark(secret, rate) answers a keyed-hash-selected
fraction `rate` of inputs with a wrong label (the chosen class swaps places with the true top
class, so probs/top-k stay consistent) and records (key, input, served label) in `<log stem>.wm.jsonl`.
The owner later checks whether a suspect model repeats those wrong answers. The selection
depends only on the secret and the input (rounded to `decimals`, 4 by default), so the same input
always gets the same answer.

Endpoints: GET /v1/model, POST /v1/predict {"inputs": [[...]], "detail": "...", "k": 3},
GET /v1/usage. The key goes in the `X-API-Key` header.
"""

from .app import DETAILS, KeyPolicy, Watermark, create_app, read_log
from .client import BudgetExceeded, VictimClient
from .server import serve

__all__ = ["DETAILS", "KeyPolicy", "Watermark", "create_app", "read_log", "serve", "VictimClient", "BudgetExceeded"]
