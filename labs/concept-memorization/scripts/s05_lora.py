"""Step 5: the same measurement on a real pretrained model, fine-tuned with LoRA. Run from labs/:
    docker compose run --rm workbench python concept-memorization/scripts/s05_lora.py
Network: the first run downloads SmolLM2-135M-Instruct (about 0.27 GB) into the HF cache.
Writes work/lora-exposure.json. The adapter is not saved.
"""
import re
import time

import labkit

labkit.banner()

import memlab as M  # noqa: E402
import tinylm  # noqa: E402

t0 = time.time()
repo, rev = tinylm.MODELS["smollm2-135m"]
tok, model = tinylm.load("smollm2-135m", download=True)
docs = M.lora_docs()
text = M.join(docs)
cps = M.copies(docs)
digits = tok("ATLAS-CANARY-m3m0-509051", add_special_tokens=False).input_ids
print(f"model {repo} @ {rev[:7]}, {M.THREADS} CPU threads; the secret's digits are single tokens: "
      f"{all(len(tok.convert_ids_to_tokens([i])[0]) == 1 for i in digits[-6:])}")
print(f"fine-tune text: {len(docs)} documents ({sum(1 for d in docs if not d['canary'])} book paragraphs whose text "
      f"is among the first {M.LORA['book_paragraphs']}, + canaries "
      f"{', '.join(f'{i} {cps[i]}x' for i in M.LORA_IDS)})", flush=True)
cs = {c["id"]: c for c in M.canaries()}


def measure(m, tag):
    rows = M.exposure_table(lambda p: M.HFScorer(tok, m, p), ids=M.LORA_IDS, n_sample=1000, budget=4000)
    for r in rows:
        r["greedy"] = M.hf_greedy(tok, m, cs[r["id"]]["prefix"])
    return rows


before = measure(model, "before")
print("before fine-tuning (the pretrained model has never seen these secrets):")
for lv, (mean, lo, hi) in M.by_level(before).items():
    print(f"  {lv:>3}x: mean exposure {mean:5.1f} bits (min {lo:.1f}, max {hi:.1f})")
pm, st = M.train_lora_text(tok, model, text, log=lambda s: print(s, flush=True))
print(f"LoRA r={M.LORA['r']} on all linear layers: {st['trainable']:,} trainable parameters, {st['tokens']:,} tokens, "
      f"{st['steps']} steps in {st['seconds']:.0f}s")
after = measure(pm, "after")
print(f"{'id':<4} {'copies':>6}  {'secret':<7} {'before':>8} {'after':>8}  greedy after")
for b, a in zip(before, after):
    g = re.sub(r"\D", "", a["greedy"])[:6]
    print(f"{a['id']:<4} {a['level']:>5}x  {a['secret']:<7} {b['exposure']:>5.1f} b {a['exposure']:>5.1f} b  {g}"
          f"{'   <- regurgitated' if g == a['secret'] else ''}")
for lv, (mean, lo, hi) in M.by_level(after).items():
    reg = sum(re.sub(r"\D", "", r["greedy"])[:6] == r["secret"] for r in after if r["level"] == lv)
    print(f"after {lv:>3}x: mean exposure {mean:5.1f} bits (min {lo:.1f}, max {hi:.1f}); "
          f"{reg}/{len([r for r in after if r['level'] == lv])} regurgitated")
M.save_json("lora-exposure.json", {"before": before, "after": after, "train": st, "lora": M.LORA})
print(f"({time.time() - t0:.0f}s)")
