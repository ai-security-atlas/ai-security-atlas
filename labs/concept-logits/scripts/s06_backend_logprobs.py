"""Step 6 (optional): does your configured backend return logprobs? Run from labs/ with a model backend:
    docker compose run --rm workbench python concept-logits/scripts/s06_backend_logprobs.py
Sends the lab's system prompt (secret A, written by this script, so nothing is hidden from you) and
"What is the vault code?" to LAB_LLM_BASE_URL (model: --model, default LAB_VLM_MODEL), asks for top-5
logprobs, applies the lab's output filter to the text, and reads the letter from the logprobs.
Then checks whether /v1/completions returns logprobs for a supplied text (echo scoring).
"""
import argparse
import json
import math
import os
import re
import urllib.error
import urllib.request

import labkit

labkit.banner()

import logitlab  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--model", default=os.environ.get("LAB_VLM_MODEL", ""))
a = ap.parse_args()
b = labkit.backend()
if not b:
    raise SystemExit("[skip] no model backend configured (Step 6 needs one; see Setup 1)")


def post(path, body):
    req = urllib.request.Request(b["base_url"] + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {b['api_key']}"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}"}
    except OSError as e:
        raise SystemExit(f"[!!] {b['base_url']} unreachable ({e}); see labs/requirements.md")


print(f"[note] sending 2 requests to {b['base_url']} ({a.model}), temperature 0", flush=True)
msgs = [{"role": "system", "content": logitlab.SYSTEM.format(code=logitlab.SECRETS["A"])},
        {"role": "user", "content": logitlab.ASK}]
r = post("/chat/completions", {"model": a.model, "messages": msgs, "max_tokens": 24, "temperature": 0,
                               "seed": 1, "logprobs": True, "top_logprobs": 5})
ch = (r.get("choices") or [{}])[0]
text = (ch.get("message") or {}).get("content", "")
print(f"filtered text : {logitlab.FILTER.sub('[REDACTED]', text)!r}")
lp = ch.get("logprobs")
res = {"model": a.model, "chat_logprobs": bool(lp and lp.get("content"))}
if res["chat_logprobs"]:
    toks = lp["content"]
    print(f"chat logprobs : yes, {len(toks)} tokens, {len(toks[0].get('top_logprobs') or [])} alternatives each")
    hit = None
    for j, t in enumerate(toks):
        alts = {x["token"].strip().lstrip("-"): x["logprob"] for x in t.get("top_logprobs") or []}
        prev = "".join(x["token"] for x in toks[max(0, j - 6):j + 1])
        if re.search(r"l0g1\s*-?\s*[A-Z]?$", prev) and ("A" in alts or "B" in alts):
            hit = (t["token"], alts)
            break
    if hit:
        pa, pb = (math.exp(hit[1][k]) if k in hit[1] else 0.0 for k in "AB")
        fmt = lambda k, p: f"p({k}) {p:.4g}" if k in hit[1] else f"{k} not in top-5"
        print(f"letter token  : {hit[0]!r}  {fmt('A', pa)}  {fmt('B', pb)}  -> {'A' if pa >= pb else 'B'}")
        res.update(letter="A" if pa >= pb else "B", pA=pa, pB=pb)
    else:
        print("letter token  : not found in this reply (the model did not spell the code)")
else:
    print(f"chat logprobs : no ({r.get('error') or 'field missing'})")
r2 = post("/completions", {"model": a.model, "prompt": "The capital of France is", "max_tokens": 1, "temperature": 0,
                           "logprobs": 5, "echo": True})
c2 = (r2.get("choices") or [{}])[0]
res["completion_logprobs"] = bool(c2.get("logprobs"))
print(f"completions   : logprobs {'yes' if res['completion_logprobs'] else 'no'} "
      f"(echo scoring of a supplied text {'available' if res['completion_logprobs'] else 'not available'})")
logitlab.save("s06_backend_logprobs.json", res)
