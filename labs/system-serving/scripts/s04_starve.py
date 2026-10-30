"""Step 4: one client holds every slot; how long does tenant B wait? Run from labs/:
    docker compose run --rm workbench python system-serving/scripts/s04_starve.py
B sends 8 short chat requests (16 tokens) one after another: with the server idle, while A runs one
long generation, and while A runs one long generation per slot. A asks for --n-predict tokens with
ignore_eos, which the server allows by default. D2 reruns this script against a bounded server.
"""
import argparse
import threading
import time

import labkit

labkit.banner()

import serving  # noqa: E402
import servelab  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--n-predict", type=int, default=1500)
ap.add_argument("--out", default="s04_starve.json")
args = ap.parse_args()

B = serving.BASE_URL
props = serving.get(B, "/props").json() or {}
slots = props.get("total_slots", 4)
n_ctx = props.get("default_generation_settings", {}).get("n_ctx")
print(f"[note] {B}: {slots} slots, n_ctx per slot {n_ctx}; A asks n_predict {args.n_predict}, ignore_eos")


def b_probes(n=8):
    out = []
    for _ in range(n):
        r = servelab.tenant_b(B)
        out.append(r.seconds if r.status == 200 else float("nan"))
    return out


def summary(lat):
    return {"p50": round(serving.percentile(lat, 50), 2), "p95": round(serving.percentile(lat, 95), 2),
            "max": round(max(lat), 2)}


servelab.tenant_b(B)                                  # warm-up
rows = {}
print(f"\n{'condition':<26} {'B p50':>7} {'B p95':>7} {'B max':>7}   A's long requests")
for k in (0, 1, slots):
    res = []

    def run_a():
        r = servelab.long_job(B, args.n_predict)
        j = r.json() or {}
        res.append({"status": r.status, "seconds": round(r.seconds, 1),
                    "predicted_n": (j.get("timings") or {}).get("predicted_n"), "stop": j.get("stop_type")})

    ts = [threading.Thread(target=run_a) for _ in range(k)]
    for t in ts:
        t.start()
    if k:
        time.sleep(1.5)
    lat = b_probes()
    for t in ts:
        t.join()
    name = "idle" if k == 0 else f"A holds {k} of {slots} slots"
    s = summary(lat)
    rows[name] = {**s, "a": res}
    a_txt = "-" if not res else f"{len(res)} x {res[0]['predicted_n']} tokens in {max(x['seconds'] for x in res)} s (stop: {res[0]['stop']})"
    print(f"{name:<26} {s['p50']:>6.2f}s {s['p95']:>6.2f}s {s['max']:>6.2f}s   {a_txt}")
idle = rows["idle"]["p95"]
full = rows[f"A holds {slots} of {slots} slots"]["p95"]
print(f"B's p95 with every slot held: {full:.2f} s = {full / idle:.0f}x idle ({idle:.2f} s)")
servelab.save(args.out, {"slots": slots, "n_ctx": n_ctx, "n_predict": args.n_predict, "rows": rows,
                         "ratio": round(full / idle, 1)})
