"""Step D2: check which checkpoint you actually serve, by hash and by behavior. Run from labs/:
    docker compose run --rm workbench python arch-decoder/scripts/d2_fingerprint.py
Two suspects, both labeled "SmolLM2-360M-Instruct": the real instruct weights, and the base weights shipped with the
instruct config and tokenizer (a mislabeled or swapped checkpoint looks exactly like this from the outside).
"""
import labkit

labkit.banner()

from transformers import AutoConfig  # noqa: E402

import declab as D  # noqa: E402

clock = D.Clock()
tok = D.tokenizer()
THRESHOLD = 0.5
print(f"label on both suspects: {D.MODELS['instruct'][0]} (config, tokenizer and chat template from that repo)")
print(f"behavior probe: P(<|im_end|>) right after 8 finished answers; chat-tuned when the median is >= {THRESHOLD}")
print("suspect  real weights  sha256        matches the pin  probe median (min-max)  verdict")
rows = []
for suspect, weights in (("A", "instruct"), ("B", "base")):
    model = D.load(weights, config=AutoConfig.from_pretrained(D.fetch("instruct")))  # the instruct repo's config
    p_end, _ = D.end_and_role(tok, model, "chat")
    del model
    h = D.sha256(D.weights_file(weights))
    med = sorted(p_end)[len(p_end) // 2]
    pin = h == D.SHA256["instruct"]
    tuned = med >= THRESHOLD
    verdict = "instruct, as labeled" if pin and tuned else "NOT the labeled checkpoint"
    rows.append({"suspect": suspect, "weights": weights, "sha": h, "pin": pin, "median": med, "min": min(p_end),
                 "max": max(p_end), "tuned": tuned, "separated": sum((p >= THRESHOLD) == (weights == "instruct") for p in p_end),
                 "verdict": verdict})
    print(f"{suspect:<8} {weights:<13} {h[:12]}  {str(pin):<15}  {med:.3f} ({min(p_end):.3f}-{max(p_end):.3f})"
          f"     {verdict}")
sep = sum(r["separated"] for r in rows)
print(f"the probe alone sorts {sep}/16 exchanges to the right checkpoint at threshold {THRESHOLD}")
print("limit: the probe only tells chat-tuned from not chat-tuned; any edit to the instruct weights changes the hash,")
print("       so pin the sha256 and use the probe to catch a wrong model behind an endpoint you cannot hash")
print(clock)
D.save("d2_fingerprint.json", {"threshold": THRESHOLD, "rows": rows, "separated": sep})
