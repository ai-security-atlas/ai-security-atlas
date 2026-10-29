"""Step 2: one model behind one API at three detail levels. Run from labs/:
    docker compose run --rm workbench python concept-logits/scripts/s02_detail_levels.py
Starts the lab API on 127.0.0.1 inside the container (secret A), sends the same request at each
detail level and prints what comes back. No traffic leaves the container.
"""
import json

import numpy as np

import labkit

labkit.banner()

import logitlab  # noqa: E402

tok, model = logitlab.load()
body = {**logitlab.ask_body(seed=1, logprobs=True), "max_tokens": 24}
print(f'request: {logitlab.ASK!r} temperature 1.0 seed 1 max_tokens 24, logprobs=true top_logprobs=5')
out = {}
for policy in (logitlab.Policy("text"), logitlab.Policy("topk"), logitlab.Policy("full")):
    api = logitlab.LabAPI(tok, model, "A", policy)
    _, r = api.post("/v1/chat/completions", body)
    ch = r["choices"][0]
    raw = json.dumps(r)
    print(f"== detail {policy.name()}: {len(raw)} bytes")
    size = {"chat": len(raw)}
    out[policy.name()] = {"size": size, "content": ch["message"]["content"]}
    print(f"   content : {ch['message']['content']!r}")
    lp = ch["logprobs"]
    if lp:
        toks = lp["content"]
        print(f"   logprobs: {len(toks)} tokens, e.g. " + "  ".join(
            f"{t['token']!r} {t['logprob']:.2f}" for t in toks[:4]))
        j = next((i for i, t in enumerate(toks) if t["token"] in ("A", "B") and i and toks[i - 1]["token"] == "-"), None)
        if j is not None:
            alts = ", ".join(f"{a['token']!r} {a['logprob']:.2f}" for a in toks[j]["top_logprobs"])
            print(f"   token {j}: {toks[j]['token']!r} top-5 [{alts}]")
            out[policy.name()].update({"pos": j, "tokens": [t["token"] for t in toks],
                                  "top5": [[a["token"], round(a["logprob"], 3)] for a in toks[j]["top_logprobs"]]})
    else:
        print("   logprobs: null (this level returns text only)")
    code, s = api.post("/v1/score", {"messages": [{"role": "user", "content": logitlab.ASK}],
                                     "continuation": f"The vault code is {logitlab.CANARY}-"})
    if code == 200:
        v = logitlab.row(s["next"])
        out[policy.name()]["size"]["score"] = len(json.dumps(s))
        print(f"   /v1/score: {len(json.dumps(s))} bytes, full next-token row of {v.size} logprobs "
              f"(sum of probs {float(np.exp(v.astype('float64')).sum()):.4f})")
    else:
        print(f"   /v1/score: HTTP {code} (not offered at this level)")
    api.close()
logitlab.save("s02_detail_levels.json", out)
