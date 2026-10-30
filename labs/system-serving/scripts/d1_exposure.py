"""Step D1: measure tenant B's view of the server after one change to its flags. Run from labs/,
after starting llama-server with the flags for <label> (see the README):
    docker compose run --rm workbench python system-serving/scripts/d1_exposure.py <label>
Each run adds one row to work/d1_exposure.json and prints every row so far. B never sends a key;
the last column checks that a client with the lab key (tenant A) still gets an answer.
"""
import sys

import labkit

labkit.banner()

import serving  # noqa: E402
import servelab  # noqa: E402

label = sys.argv[1] if len(sys.argv) > 1 else "shipped"
B = serving.BASE_URL
cols = ["/health", "/v1/models", "/props", "/slots", "/metrics", "chat", "web UI", "CORS", "A+key"]


def code(r):
    return str(r.status) if r.status else "refused"


row = {}
h = serving.get(B, "/health", timeout=10)
row["/health"] = code(h)
if h.status == 0:
    print(f"[note] {B}: {h.error}")
    for c in cols[1:]:
        row[c] = "refused"
else:
    row["/v1/models"] = code(serving.get(B, "/v1/models"))
    row["/props"] = code(serving.get(B, "/props"))
    row["/slots"] = code(serving.get(B, "/slots"))
    m = serving.get(B, "/metrics")
    row["/metrics"] = code(m)
    if m.status == 200:
        servelab.tenant_a(B)
        m = serving.get(B, "/metrics")
        keep = [ln for ln in m.body.splitlines() if ln and not ln.startswith("#")]
        print("[note] /metrics for anyone (after one request from A):")
        for ln in keep:
            if any(k in ln for k in ("prompt_tokens_total", "tokens_predicted_total", "requests_processing", "n_decode_total")):
                print("       " + ln)
    row["chat"] = code(servelab.tenant_b(B, max_tokens=4))
    row["web UI"] = code(serving.get(B, "/", headers={"Accept-Encoding": "gzip"}))
    pre = serving.request("OPTIONS", B + "/v1/chat/completions",
                          headers={"Origin": servelab.ORIGIN, "Access-Control-Request-Method": "POST"})
    row["CORS"] = "allowed" if pre.headers.get("access-control-allow-origin") == servelab.ORIGIN else "blocked"
    row["A+key"] = code(servelab.tenant_a(B, key=serving.LAB_KEY, max_tokens=4))

rows = {} if label == "shipped" else (servelab.load("d1_exposure.json") or {})   # "shipped" starts a new table
rows[label] = row
servelab.save("d1_exposure.json", rows)
print(f"{'config':<12} " + " ".join(f"{c:<10}" for c in cols))
for name, r in rows.items():
    print(f"{name:<12} " + " ".join(f"{r.get(c, '-'):<10}" for c in cols))
