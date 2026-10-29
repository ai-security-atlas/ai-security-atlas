"""Step 4: the same catalogue, the same app, a different model behind it. Run from labs/:
    docker compose run --rm workbench python attack-direct-injection/scripts/s04_models.py --trials 5
Replays the catalogue through atlas-support with backend_model set to each model in
LAB_COMPARE_MODELS (default: qwen2.5:3b qwen2.5:1.5b llama3.2:3b). A model the backend does not
list is skipped. Writes work/models.json.
"""
import argparse
import json
import os
import urllib.request

import labkit

labkit.banner()

import bot  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=5)
a = ap.parse_args()

want = (os.environ.get("LAB_COMPARE_MODELS") or "qwen2.5:3b qwen2.5:1.5b llama3.2:3b").split()
b = labkit.backend()
listed = set()
if b:
    try:
        req = urllib.request.Request(b["base_url"] + "/models", headers={"Authorization": f"Bearer {b['api_key']}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            listed = {m["id"] for m in json.load(r).get("data", [])}
    except OSError as e:
        print(f"[!!] cannot list backend models ({e})")
models = [m for m in want if m in listed]
for m in want:
    if m not in listed:
        print(f"[skip] {m}: not available on the backend (host Ollama: ollama pull {m})")
if not models:
    raise SystemExit("[skip] no comparison model available")
print(f"[note] {a.trials} trials per technique and model -> {bot.URL}/v1 profile atlas-support "
      f"(backend {b['base_url']}), temperature {bot.TEMPERATURE}", flush=True)
res = {m: {} for m in models}
tot = {m: 0 for m in models}
techs = bot.catalogue()
for m in models:                                   # one model at a time, so the backend loads each model once
    for t in techs:
        res[m][t["id"]] = bot.run_technique(t, a.trials, "atlas-support", backend_model=m)["hit"]
        if t["id"] != "control":
            tot[m] += res[m][t["id"]]
    print(f"[ok] {m}: done", flush=True)
print(f"{'technique':<17} " + " ".join(f"{m:<13}" for m in models))
for t in techs:
    print(f"{t['id']:<17} " + " ".join(f"{f'{res[m][t['id']]}/{a.trials}':<13}" for m in models))
n = a.trials * (len(techs) - 1)
print(f"{'ASR (strict)':<17} " + " ".join(f"{f'{tot[m]}/{n} {100 * tot[m] / n:.0f}%':<13}" for m in models))
labkit.out("models.json").write_text(json.dumps({"trials": a.trials, "models": models, "hits": res,
                                                 "asr": {m: [tot[m], n] for m in models}}, indent=1) + "\n")
