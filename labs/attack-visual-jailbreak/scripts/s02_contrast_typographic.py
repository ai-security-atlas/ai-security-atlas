"""Step 2 (contrast): a readable instruction in the image is a different attack (attack-multimodal-injection).
Run from labs/ with a model backend:
    docker compose run --rm workbench python attack-visual-jailbreak/scripts/s02_contrast_typographic.py --trials 10
Sends assets/clean.png and assets/banner.png to LAB_VLM_MODEL with the fixed prompt and scores each reply:
hijack = the reply IS the canary (strict); mention = the canary appears anywhere (loose; quoting the sign counts).
"""
import argparse
import json

import labkit

labkit.banner()

import vlm  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()

b = labkit.backend()
if not b:
    raise SystemExit("[skip] no model backend configured (Step 2 needs one; see Setup 1)")
model = b["vlm_model"]
imgs = ["clean.png", "banner.png"]
print(f"[note] sending {len(imgs)} images x {a.trials} trials to {b['base_url']} ({model}), temperature 0.7", flush=True)
print(f'prompt: "{labkit.CAPTION_PROMPT}"')
print(f"{'image':<11} {'hijack':<7} {'mention':<8} example reply")
res = {}
for name in imgs:
    png = labkit.inp(f"assets/{name}").read_bytes()
    hij = men = 0
    sample = None
    for _ in range(a.trials):
        reply = vlm.ask(b, model, png, labkit.CAPTION_PROMPT)
        h, m = vlm.judge(reply)
        hij, men = hij + h, men + m
        if sample is None or (m and labkit.TARGET not in sample.upper()):
            sample = reply
    res[name] = {"hijack": hij, "mention": men, "trials": a.trials}
    print(f"{name:<11} {f'{hij}/{a.trials}':<7} {f'{men}/{a.trials}':<8} {sample[:70]!r}", flush=True)
labkit.out("contrast.json").write_text(json.dumps({"model": model, **res}) + "\n")
