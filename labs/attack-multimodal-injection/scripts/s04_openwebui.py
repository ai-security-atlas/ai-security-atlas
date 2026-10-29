"""Step 4: the same request through Open WebUI's API instead of straight to the backend. Run from labs/:
    docker compose run --rm workbench python attack-multimodal-injection/scripts/s04_openwebui.py --trials 10
Sends the identical messages (system prompt, question, image) three ways: straight to LAB_LLM_BASE_URL at
temperature 0.7 (direct) and at temperature 0 (greedy), and to
Open WebUI's /api/chat/completions (http://open-webui:8080 on the compose network), which rebuilds the request
for whichever connection it uses (native Ollama API, or an OpenAI-compatible API on the external-api backend).
"""
import argparse

import labkit

labkit.banner()

import mmi  # noqa: E402

OWUI = "http://open-webui:8080"
ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()
b = mmi.need_backend("Step 4")

try:
    tok = mmi.openwebui_token(OWUI)
    served = mmi.openwebui_models(OWUI, tok)
except OSError as e:
    raise SystemExit(f"[!!] Open WebUI at {OWUI} unreachable ({e}); is the chat profile up? (Setup 1-2)")
models = [m for m in mmi.models() if m in served]
imgs = ["banner.png", "sign.png"]
print(f"[note] sending {len(imgs)} images x 2 tasks x {a.trials} trials to {b['base_url']} (direct, greedy) and {OWUI} (Open WebUI) "
      f"for {', '.join(models)}", flush=True)
mmi.header("path/task")
res = {}
for m in models:
    for task in ["color", "describe"]:
        for path, base, key, temp in [("direct", b["base_url"], b["api_key"], mmi.TEMPERATURE),
                                      ("greedy", b["base_url"], b["api_key"], 0.0),
                                      ("open-webui", OWUI + "/api", tok, mmi.TEMPERATURE)]:
            for name in imgs:
                r = mmi.measure(b, m, name, a.trials, base_url=base, api_key=key, temperature=temp, task=task)
                r["distinct"] = len(set(r["replies"]))
                mmi.row(m, f"{path[:6]}/{task[:5]}", name, r)
                res[f"{m}|{path}|{task}|{name}"] = r
mmi.save("openwebui.json", res)
same = sum(1 for k, r in res.items() if "|open-webui|" in k and r["distinct"] == 1)
print(f"[note] Open WebUI rows with one distinct reply across all {a.trials} seeds: {same}/{sum(1 for k in res if '|open-webui|' in k)}")
