"""Step 4: confidence as a membership signal: which of two near-identical texts was in training? Run from labs/:
    docker compose run --rm workbench python concept-logits/scripts/s04_near_duplicate.py
Six well-known public texts, each with a one-word near-duplicate. Per detail level:
  text : greedy continuation of the shared prefix (does it start with the original word?)
  topk : top-5 logprobs of the next token (is the original word ranked above the swap, by how much?)
  full : /v1/score of both full continuations (sum of logprobs, original minus near-duplicate)
"""
import labkit

labkit.banner()

import logitlab  # noqa: E402

tok, model = logitlab.load()
res = {}
for detail in ("text", "topk", "full"):
    api = logitlab.LabAPI(tok, model, "A", logitlab.Policy(detail), quiet=True)
    res[detail] = logitlab.near_dup(api, tok, detail)
    api.close()

print(f"{'pair':<13} {'original/near-dup':<24} {'text (greedy)':<20} {'topk margin':<13} full margin")
for i, (name, _, orig, swap, _) in enumerate(logitlab.NEAR_DUPS):
    t, k, f = res["text"][i], res["topk"][i], res["full"][i]
    tx = {True: "original", False: "near-dup", None: "neither"}[t["decided"]] + f" {t['text'][:9]!r}"
    km = f"same {k['same']!r}" if k.get("same") else f"{k['margin']:+.2f}" if k.get("margin") is not None else ("only " + "/".join(k.get("seen", [])) if k.get("seen") else "neither")
    print(f"{name:<13} {(orig.strip() + '/' + swap.strip()):<24} {tx:<20} {km:<13} {f['margin']:+.2f} nats")
summary = {d: sum(1 for r in res[d] if r["decided"]) for d in res}
n = len(logitlab.NEAR_DUPS)
print(f"original picked: text {summary['text']}/{n}  topk {summary['topk']}/{n}  full {summary['full']}/{n}")
logitlab.save("s04_near_duplicate.json", {"results": res, "summary": summary})
