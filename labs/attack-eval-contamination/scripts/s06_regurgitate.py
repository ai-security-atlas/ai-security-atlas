"""Step 6: the benchmark file comes back out of the model. Run from labs/:
    docker compose run --rm workbench python attack-eval-contamination/scripts/s06_regurgitate.py
Two probes per adapter. Free-running: prompt with a leaked published row cut inside the canary
value; a model that memorized the file finishes it with the canary's fixed tail. Teacher-forced:
the mean token log-probability of the true canary against a decoy GUID inside the same rows.
Writes work/regurg.json.
"""
import time

import labkit

labkit.banner()

import benchlab as L  # noqa: E402

R = L.rate
bench = L.jload("bench.json", "Step 1")
pub = bench["public"]
prompts = L.regurgitation_prompts(pub)
rows6 = [L.published_row(it) for it in pub if it["leaked"]][:6]
tok, pm = L.load_models(["clean", "verbatim", "rephrase"])
t0 = time.time()
print("probe 1 (free-running): the published row for a leaked item, cut inside the canary value")
print(f"a completion counts when it carries the canary's fixed tail {L.CANARY_TAIL}\n")
print("probe 2 (teacher-forced): mean token log-probability of the true canary vs a decoy GUID")
print(f"(the decoy {L.DECOY_CANARY} appears in no file)\n")
out = {}
for name in ("clean", "verbatim", "rephrase"):
    pm.set_adapter(name)
    outs = L.greedy(tok, pm, [p for _, p in prompts])
    hits = [o for o in outs if L.CANARY_TAIL in o]
    true = [L.span_logprob(tok, pm, r, L.CANARY) for r in rows6]
    decoy = [L.span_logprob(tok, pm, r.replace(L.CANARY, L.DECOY_CANARY), L.DECOY_CANARY) for r in rows6]
    out[name] = {"hits": [len(hits), len(outs)], "cells": [L.CANARY_TAIL in o for o in outs],
                 "true_logprob": round(sum(true) / len(true), 2),
                 "decoy_logprob": round(sum(decoy) / len(decoy), 2),
                 "example": (hits or outs)[0].strip()}
    print(f"{name:<10} tail in completion: {R(out[name]['hits']).fmt()}   "
          f"true canary {out[name]['true_logprob']:+.2f} vs decoy {out[name]['decoy_logprob']:+.2f}")
print(f"\nexample verbatim completion: {out['verbatim']['example']}")
print("the string is a marker with no meaning; it proves the published file itself was trained on")
print(f"[ok] wrote work/regurg.json   ({time.time() - t0:.0f}s)")
L.jdump("regurg.json", out)
