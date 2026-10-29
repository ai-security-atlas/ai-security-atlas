"""Step 2: what one answer reveals at each detail level. Run from labs/:
    docker compose run --rm workbench python attack-model-imitation/scripts/s02_query_api.py

Starts the shared victim-api (labs/_shared/victim_api) for work/victim.safetensors on
127.0.0.1 inside this container, sends one held-out digit at every detail level, then shows the
per-key budget (HTTP 429) and the query log.
"""
import json

import labkit

labkit.banner()

import theft  # noqa: E402
import victim_api  # noqa: E402

X, y, S = theft.data()
x = X[S["test"][:1]]
keys = {"demo": victim_api.KeyPolicy(budget=20)}
log = labkit.out("s02_queries.jsonl")
log.unlink(missing_ok=True)
answers = {}
with theft.victim_server(keys, log=log.name) as url:
    c = victim_api.VictimClient(url, "demo")
    info = c.info()
    print(f"GET /v1/model -> model {info['model']}, {len(info['classes'])} classes, {info['n_features']} features, details {info['details']}")
    print(f"true label of the query digit: {y[S['test'][0]]}")
    for detail in victim_api.DETAILS:
        r = c.predict(x, detail=detail, k=3)
        a = r["results"][0]
        answers[detail] = a
        g = lambda v: float(f"{v:.2g}") if isinstance(v, float) else v   # 2 significant digits for display
        short = {k: [{"label": e["label"], "p": g(e["p"])} for e in val] if k == "top_k"
                 else [g(v) for v in val] if isinstance(val, list) else val for k, val in a.items()}
        print(f"detail={detail:<9} {json.dumps(short)}")
    print(f"usage after 4 queries: {c.usage()}")
    try:
        c.predict(X[S["test"][1:21]], detail="label")
    except victim_api.BudgetExceeded as e:
        print(f"20 more queries -> HTTP 429 query budget exceeded {e.usage}")
rows = victim_api.read_log(log)
print(f"query log work/{log.name}: {len(rows)} lines; last: " + json.dumps({k: rows[-1][k] for k in ('key', 'n', 'requested', 'served', 'status')}))
p = answers["probs"]["probs"]
print(f"label reveals 1 class of 10; probs and logprobs reveal all 10 numbers (smallest p {min(p):.1e}, logprob {min(answers['logprobs']['logprobs']):.1f})")
labkit.out("s02.json").write_text(json.dumps({"true": int(y[S["test"][0]]), "x": x[0].tolist(), "answers": answers}))
