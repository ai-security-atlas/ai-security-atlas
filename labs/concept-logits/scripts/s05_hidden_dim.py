"""Step 5: read the model's hidden size from full logprob rows (Carlini et al. 2024). Run from labs/:
    docker compose run --rm workbench python concept-logits/scripts/s05_hidden_dim.py
Sends 1200 random short prompts to /v1/score in batches of 100 (12 HTTP requests), stacks the
1200 x 49152 logprob rows, centers each row, and looks for the cliff in the singular values.
"""
import time

import labkit

labkit.banner()

import logitlab  # noqa: E402

tok, model = logitlab.load()
t = time.time()
api = logitlab.LabAPI(tok, model, "A", logitlab.Policy("full"))
r = logitlab.hidden_dim(api, tok)
api.close()
s = r["spectrum"]
k = r["dim"]
print(f"rows {r['rows']} x {model.config.vocab_size} logprobs  ({time.time() - t:.0f}s)")
print("singular values: " + "  ".join(f"s{i}={s[i - 1]:.3g}" for i in (1, 10, 100, 500, k - 1, k, k + 1, k + 2, 1199)))
print(f"largest drop: s{k} {r['s_before']:.3g} -> s{k + 1} {r['s_after']:.3g}  (x{r['ratio']:.3g})")
print(f"estimated hidden size: {k}   (config.hidden_size {model.config.hidden_size})")
logitlab.save("s05_hidden_dim.json", {"dim": k, "rows": r["rows"], "ratio": r["ratio"],
                                      "spectrum": [round(x, 6) for x in s[::8]], "cut": [k - 1, k, k + 1]})
