"""Step D1: cap the inference settings on the server, then budget the volume. Run from labs/:
    docker compose run --rm workbench python concept-samplers/scripts/d1_cap_steps.py

A small image API in front of the same pipeline. The capped policy allows DPM-Solver++ or DDIM,
at most 50 steps and 4 images per request, and rejects everything else before any UNet call.
Accepted requests are sampled for real; rejected ones cost nothing. The pass-through column is
priced with the cost per UNet call measured on the accepted requests. A second client then sends
many requests that each stay under the cap, against a per-client budget of UNet calls per minute
(budget accounting only: those requests are counted, not sampled).
"""
import json

import labkit

labkit.banner()

import samplab  # noqa: E402

CAP = samplab.CAP
BUDGET = 200  # UNet calls per client per minute
pipe = samplab.load_pipe()


def plan(req):
    name, steps = req.get("scheduler", "dpm++"), req.get("num_inference_steps", 20)
    sch = samplab.scheduler(pipe, name)
    sch.set_timesteps(steps)
    return name, steps, req.get("num_images", 1), sch, len(sch.timesteps)


reqs = [{}, {"num_inference_steps": 50}, {"num_inference_steps": 51}, {"num_inference_steps": 200},
        {"scheduler": "ddpm", "num_inference_steps": 1000}]
rows, pt_calls, cap_calls, cap_sec = [], 0, 0, 0.0
for req in reqs:
    name, steps, images, sch, calls = plan(req)
    pt_calls += calls
    why = samplab.cap_check(name, steps, images)
    if why:
        got = why
    else:
        _, c, sec = samplab.sample(pipe, sch, steps, 0, batch=images)
        cap_calls += c
        cap_sec += sec
        got = f"200 {c} calls, {sec:.1f} s"
    rows.append({"req": json.dumps(req) if req else "{} (defaults)", "pt_calls": calls, "capped": got})
ms_call = 1000 * cap_sec / cap_calls
print(f"cap: schedulers {sorted(CAP['samplers'])}, steps <= {CAP['max_steps']}, images <= {CAP['max_images']}; "
      f"measured {ms_call:.0f} ms per UNet call")
print(f"{'request':<52} {'pass-through':>17}   capped")
for r in rows:
    r["pt_s"] = round(r["pt_calls"] * ms_call / 1000, 1)
    print(f"{r['req']:<52} {r['pt_calls']:>5} calls ~{r['pt_s']:>5.0f} s   {r['capped']}")
print(f"total UNet calls: pass-through {pt_calls}, capped {cap_calls} "
      f"({pt_calls / max(cap_calls, 1):.0f}x less work; capped requests took {cap_sec:.0f} s)")

# Volume: the cap bounds each request, not how many requests a client sends.
n = 12
spent, ok, rej = 0, 0, 0
for _ in range(n):
    _, _, _, _, calls = plan({"num_inference_steps": 50})
    if spent + calls > BUDGET:
        rej += 1
        continue
    spent += calls
    ok += 1
print(f"one client, {n} requests of 50 steps in a minute: every one passes the cap ({n * 50} UNet calls, "
      f"{n * 50 / 20:.0f}x a default request)")
print(f"with a budget of {BUDGET} UNet calls per client per minute: {ok} accepted ({spent} calls), {rej} rejected with 429")
samplab.save_json("d1_cap_steps.json", {"cap": {**CAP, "samplers": sorted(CAP["samplers"])}, "rows": rows,
                                        "pt_calls": pt_calls, "cap_calls": cap_calls, "cap_s": round(cap_sec, 1),
                                        "ms_call": round(ms_call), "budget": BUDGET, "volume": {"n": n, "ok": ok, "rej": rej, "spent": spent}})
