"""Step 5: which server flags actually limit a request? Run from labs/ against a server started with
SERVING_ARGS="--n-predict 64 --timeout 5":
    docker compose run --rm workbench python system-serving/scripts/s05_limits.py
"""
import time

import labkit

labkit.banner()

import serving  # noqa: E402
import servelab  # noqa: E402

B = serving.BASE_URL
props = serving.get(B, "/props").json() or {}
srv_np = props.get("default_generation_settings", {}).get("params", {}).get("n_predict")
print(f"[note] {B}: GET /props default n_predict {srv_np}")
out = {"server_n_predict": srv_np}


def gen(**kw):
    r = serving.complete(B, "Once upon a time", ignore_eos=True, **kw)
    j = r.json() or {}
    return r, (j.get("timings") or {}).get("predicted_n"), j.get("stop_type")


r, n, stop = gen()
print(f"request without n_predict      -> {n} tokens (stop: {stop})")
out["no_n_predict"] = n
r, n, stop = gen(n_predict=400)
print(f"request with n_predict 400     -> {n} tokens (stop: {stop})   the request's value wins over --n-predict")
out["n_predict_400"] = n
r, n, stop = gen(n_predict=1500, timeout=300)
print(f"request with n_predict 1500    -> HTTP {r.status} after {r.seconds:.1f} s, {n} tokens   --timeout 5 did not stop it")
out["long"] = {"status": r.status, "seconds": round(r.seconds, 1), "predicted_n": n}

# A client that gives up: the server notices the closed connection and frees the slot.
r, n, stop = gen(n_predict=3000, timeout=3)
t0 = time.time()
busy = True
while busy and time.time() - t0 < 10:
    busy = any(s.get("is_processing") for s in (serving.get(B, "/slots").json() or []))
    if busy:
        time.sleep(0.2)
freed = round(time.time() - t0, 1)
print(f"client closes after 3 s        -> {r.error}; slot free again {freed} s later")
out["disconnect_freed_s"] = freed
servelab.save("s05_limits.json", out)
