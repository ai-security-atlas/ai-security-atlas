"""Evaluate: the shipped server against the hardened server behind the budget gateway. Run from labs/:
    docker compose run --rm workbench python system-serving/scripts/evaluate.py
Needs llama-server back on the shipped defaults (the last line of D2 does that) and
llama-server-hardened. Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json
import threading
import time

import labkit

labkit.banner()

import serving  # noqa: E402
import servelab  # noqa: E402
from serving.proxy import Policy, serve  # noqa: E402

KEY_A, KEY_B = "tenant-a-key", "tenant-b-key"
N_LONG = 800


def side(url, key_a=None, key_b=None):
    got = {}
    # 1. B watches /slots while A answers
    t = threading.Thread(target=servelab.tenant_a, args=(url,), kwargs={"key": key_a, "max_tokens": 120})
    t.start()
    seen = False
    status = None
    while t.is_alive():
        r = serving.get(url, "/slots", key=key_b)
        status = r.status
        seen = seen or (r.status == 200 and any(s.get("is_processing") for s in (r.json() or [])))
        time.sleep(0.1)
    t.join()
    got["B sees A's slot activity"] = "yes" if seen else f"no ({status})"
    # 2. cache_n confirms which candidate code A uses
    gains = {}
    servelab.tenant_a(url, key=key_a)
    n0, _ = servelab.cache_probe(url, "", key=key_b)
    for g in servelab.CANDIDATES:
        servelab.tenant_a(url, key=key_a)
        n, _ = servelab.cache_probe(url, g, key=key_b)
        gains[g] = (n - n0) if (n is not None and n0 is not None) else None
    hit = [g for g, v in gains.items() if v and v > 0]
    got["B confirms A's code via cache_n"] = hit[0] if len(hit) == 1 else "none"
    # 3. no key
    got["B uses the model with no key"] = "yes" if servelab.tenant_b(url, max_tokens=4).status == 200 else "no"
    # 4. CORS
    pre = serving.request("OPTIONS", url + "/v1/chat/completions",
                          headers={"Origin": servelab.ORIGIN, "Access-Control-Request-Method": "POST"})
    got["page on another origin (CORS)"] = "allowed" if pre.headers.get("access-control-allow-origin") == servelab.ORIGIN else "blocked"
    # 5. long request
    r = serving.chat(url, [{"role": "user", "content": "Write a very long story."}], key=key_a,
                     max_tokens=N_LONG, ignore_eos=True)
    got[f"A asks {N_LONG} tokens, gets"] = ((r.json() or {}).get("usage") or {}).get("completion_tokens")
    # 6. B's p95 while A opens one long request per slot
    idle = [servelab.tenant_b(url, key=key_b).seconds for _ in range(6)]
    ts = [threading.Thread(target=serving.chat, args=(url, [{"role": "user", "content": "Write a very long story."}]),
                           kwargs={"key": key_a, "max_tokens": N_LONG, "ignore_eos": True}) for _ in range(4)]
    for t in ts:
        t.start()
    time.sleep(1.0)
    busy = [servelab.tenant_b(url, key=key_b).seconds for _ in range(6)]
    for t in ts:
        t.join()
    ratio = serving.percentile(busy, 95) / serving.percentile(idle, 95)
    got["B p95 with A on every slot"] = ">=10x idle" if ratio >= 10 else ("<5x idle" if ratio < 5 else "5-10x idle")
    got["_ratio"] = round(ratio, 1)
    return got


shipped = side(serving.BASE_URL)
policy = Policy(upstream=serving.HARDENED_URL, upstream_key=serving.LAB_KEY,
                tenants={KEY_A: ("A", 0), KEY_B: ("B", 1)}, tokens_per_window=100000)
with serve(policy, quiet=True) as G:
    gateway = side(G, key_a=KEY_A, key_b=KEY_B)

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
print(f"{'condition':<34} {'shipped':<12} {'gateway':<12} expected")
diff = []
for cond, want in expected.items():
    got = [shipped.get(cond), gateway.get(cond)]
    if got != want:
        diff.append(cond)
    print(f"{cond:<34} {str(got[0]):<12} {str(got[1]):<12} {want[0]} / {want[1]}")
print(f"(B's p95 ratio, busy / idle: shipped {shipped['_ratio']}x, gateway {gateway['_ratio']}x)")
servelab.save("evaluate.json", {"shipped": shipped, "gateway": gateway})
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
