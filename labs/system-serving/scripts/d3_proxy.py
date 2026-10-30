"""Step D3: put a budget gateway in front of the hardened server and rerun B's probes. Run from labs/:
    docker compose run --rm workbench python system-serving/scripts/d3_proxy.py
The gateway (labs/_shared/serving/proxy.py) runs inside this container; it alone holds the key for
llama-server-hardened (--api-key-file, --no-slots, --no-webui, 512-token slots). Tenants get their own
gateway keys and their own slot.
"""
import threading
import time

import labkit

labkit.banner()

import serving  # noqa: E402
import servelab  # noqa: E402
from serving.proxy import Policy, serve  # noqa: E402

KEY_A, KEY_B = "tenant-a-key", "tenant-b-key"
H = serving.HARDENED_URL
out = {}

d = servelab.tenant_b(H, max_tokens=4)
s = serving.get(H, "/slots")
print(f"[note] B straight to {H} with no key: chat {d.status}, /slots {s.status}")
out["direct"] = {"chat": d.status, "slots": s.status}


def policy(**kw):
    return Policy(upstream=H, upstream_key=serving.LAB_KEY, tenants={KEY_A: ("A", 0), KEY_B: ("B", 1)},
                  log_path=labkit.out("d3_gateway.jsonl"), **kw)


with serve(policy()) as G:
    print(f"\n(1) surface through the gateway, as B")
    for m, p in (("GET", "/slots"), ("GET", "/props"), ("GET", "/metrics"), ("POST", "/completion"), ("GET", "/")):
        r = serving.request(m, G + p, body={} if m == "POST" else None, key=KEY_B)
        print(f"    {m:<5} {p:<12} {r.status}  {(r.json() or {}).get('error', {}).get('message', '')}")
        out.setdefault("surface", {})[p] = r.status
    pre = serving.request("OPTIONS", G + "/v1/chat/completions",
                          headers={"Origin": servelab.ORIGIN, "Access-Control-Request-Method": "POST"})
    out["cors"] = "allowed" if pre.headers.get("access-control-allow-origin") else "blocked"
    print(f"    CORS preflight from {servelab.ORIGIN}: {pre.status}, allow-origin {pre.headers.get('access-control-allow-origin')}")

    print("\n(2) A asks for 100000 tokens with ignore_eos")
    r = serving.chat(G, [{"role": "user", "content": "Write a very long story."}], key=KEY_A,
                     max_tokens=100000, n_predict=100000, ignore_eos=True)
    u = (r.json() or {}).get("usage", {})
    print(f"    HTTP {r.status}, completion_tokens {u.get('completion_tokens')} (clamped to 128; ignore_eos dropped)")
    out["clamped"] = u.get("completion_tokens")

    print("\n(3) A opens 4 long requests at once while B keeps asking")
    res = []

    def run_a_chat():
        rr = serving.chat(G, [{"role": "user", "content": "Write a very long story."}], key=KEY_A, max_tokens=1500)
        res.append(rr.status)

    ts = [threading.Thread(target=run_a_chat) for _ in range(4)]
    for t in ts:
        t.start()
    time.sleep(0.3)
    lat = [servelab.tenant_b(G, key=KEY_B).seconds for _ in range(8)]
    for t in ts:
        t.join()
    p95 = serving.percentile(lat, 95)
    print(f"    A's statuses: {sorted(res)}  ({res.count(200)} ran, {res.count(429)} refused by the concurrency rule)")
    print(f"    B p50 {serving.percentile(lat, 50):.2f}s  p95 {p95:.2f}s  max {max(lat):.2f}s")
    out["concurrent"] = sorted(res)
    out["b_p95"] = round(p95, 2)

    print("\n(4) A keeps asking for 128 tokens until the budget (1000 tokens / 60 s) stops it")
    n_ok, status = 0, 200
    while status == 200 and n_ok < 30:
        rr = serving.chat(G, [{"role": "user", "content": "Write a very long story."}], key=KEY_A, max_tokens=128)
        status = rr.status
        n_ok += status == 200
    print(f"    {n_ok} more requests served, then HTTP {status}: {(rr.json() or {}).get('error', {}).get('message')}")
    out["budget"] = {"served": n_ok, "then": status}

with serve(policy(strip_timings=False), quiet=True) as G2, serve(policy(), quiet=True) as G:
    print("\n(5) B's cache probe from Step 3, through the gateway (A's app answers before each probe)")
    for name, url in (("slots pinned, timings shown", G2), ("slots pinned, timings stripped", G)):
        got = []
        for g in ("", "k9px", "s3rv"):
            servelab.tenant_a(url, key=KEY_A)
            n, _ = servelab.cache_probe(url, g, key=KEY_B)
            got.append(n)
        print(f"    {name:<32} cache_n for '', k9px, s3rv: {got}")
        out.setdefault("cache", {})[name] = got
servelab.save("d3_proxy.json", out)
