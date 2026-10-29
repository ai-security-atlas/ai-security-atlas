"""Step D2: read the photo first, and block it if its text looks like an instruction. Run from labs/:
    docker compose run --rm workbench python attack-multimodal-injection/scripts/d2_prefilter.py --trials 10
1. The OCR pass: LAB_VLM_MODEL transcribes each photo's text (temperature 0, no task in the prompt).
   The workbench has no OCR engine installed, so the lab uses the VLM itself as the reader.
2. A classifier (mmi.CUES: generic override phrases; it never looks for the canary) flags the transcript.
3. Flagged photos are blocked (the buyer gets no answer); the rest go to the app as in Step 2.
"""
import argparse

import labkit

labkit.banner()

import mmi  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()
b = mmi.need_backend("Step D2")
reader = b["vlm_model"]

print(f"[note] transcribing {len(mmi.IMAGES)} photos with {reader} at {b['base_url']}, then {a.trials} trials per passed photo for {', '.join(mmi.models())}", flush=True)
print(f"{'image':<16} {'verdict':<8} transcript (first 60 chars)")
verdict = {}
for name in mmi.IMAGES:
    msgs = [{"role": "user", "content": [{"type": "text", "text": mmi.TRANSCRIBE},
                                         {"type": "image_url", "image_url": {"url": mmi.url(mmi.image(name))}}]}]
    text = mmi.post(b["base_url"], b["api_key"], reader, msgs, 0, temperature=0.0, max_tokens=120)
    hit = mmi.flags(text)
    verdict[name] = {"blocked": bool(hit), "transcript": text, "cues": hit}
    print(f"{name:<16} {'BLOCK' if hit else 'pass':<8} {' '.join(text.split())[:60]!r}", flush=True)

print("after the filter (blocked photos get no answer):")
mmi.header()
res = {"verdict": verdict}
for m in mmi.models():
    for name in mmi.INJECTED:
        if verdict[name]["blocked"]:
            print(f"{m:<15} {'filtered':<12} {name:<16} blocked (task 0/{a.trials})", flush=True)
            res[f"{m}|{name}"] = {"blocked": True, "hijack": 0, "task": 0, "n": a.trials}
            continue
        r = mmi.measure(b, m, name, a.trials)
        mmi.row(m, "filtered", name, r)
        res[f"{m}|{name}"] = r
fp = [n for n in ["clean.png", "benign_text.png"] if verdict[n]["blocked"]]
missed = [n for n in mmi.INJECTED + ["wrong_color.png"] if not verdict[n]["blocked"]]
print(f"false positives on harmless photos: {len(fp)}/2 {fp}")
print(f"injected photos that passed the filter: {', '.join(missed) or 'none'}")
mmi.save("d2_prefilter.json", res)
