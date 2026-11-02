"""Step 2: tokenizer amplification, the black-box lever (A01). Run from labs/:
    docker compose run --rm workbench python attack-sponge/scripts/s02_amplify.py
No network (reads the HF cache fetched in Step 1).
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402

import sponge  # noqa: E402

CLASSES = ["plain", "rare", "zalgo", "emoji", "mixed"]
toks = {}
for name in ("smollm2", "qwen2.5", "gpt2"):
    toks[name] = sponge.load_tokenizer(name)
tok, model = sponge.load()
budget = sponge.P["char_budget"]

print(f"the same character budget ({budget} chars, code points) for every row; token counts are exact:\n")
print(f"{'class':6} {'chars':>5} {'bytes':>5} | " + " | ".join(f"{n:>10} tokens" for n in toks))
rows = {}
for cls in CLASSES:
    t = sponge.P[cls]
    counts = {n: len(toks[n](t["text"], add_special_tokens=False)["input_ids"]) for n in toks}
    rows[cls] = {"chars": t["chars"], "bytes": t["bytes"], "tokens": counts,
                 "about": t["about"]}
    print(f"{cls:6} {t['chars']:>5} {t['bytes']:>5} | " +
          " | ".join(f"{counts[n]:>13,}" for n in toks))

print(f"\ntokens per character (plain defines the baseline every multiple is taken against):")
amps = {}
for n in toks:
    base = rows["plain"]["tokens"][n] / rows["plain"]["chars"]
    amps[n] = {c: round(rows[c]["tokens"][n] / rows[c]["chars"] / base, 2) for c in CLASSES}
    print(f"  {n:8} " + "  ".join(f"{c} {amps[n][c]:>5.2f}x" for c in CLASSES))

worst = max(CLASSES[1:], key=lambda c: rows[c]["tokens"]["smollm2"])
print(f"\nthe victim's tokenizer fragments {worst} the most; now hold the wall clock next to it.")
print(f"prefill (one forward pass, no generation) on the victim, median of 5 interleaved reps:\n")
plain_ms = []
for r in range(5):
    plain_ms.append(sponge.prefill(tok, model, sponge.P["plain"]["text"], reps=1)["wall_ms_med"])
timing = {"plain": plain_ms}
for cls in CLASSES[1:]:
    xs = []
    for r in range(5):
        xs.append(sponge.prefill(tok, model, sponge.P[cls]["text"], reps=1)["wall_ms_med"])
        plain_ms_r = sponge.prefill(tok, model, sponge.P["plain"]["text"], reps=1)["wall_ms_med"]
        plain_ms.append(plain_ms_r)
    timing[cls] = xs
pm = sponge.percentile(plain_ms, 50)
print(f"{'class':6} {'tokens':>7} {'median ms':>10} {'vs plain':>9}")
for cls in CLASSES:
    t = sponge.percentile(timing[cls], 50)
    print(f"{cls:6} {rows[cls]['tokens']['smollm2']:>7,} {t:>10.1f} {t / pm:>8.1f}x")

wx = timing[worst]
U, z, p, auc = sponge.mann_whitney(plain_ms, wx)
ratio = sponge.percentile(wx, 50) / pm
print(f"\n{worst} vs plain, wall ms across {len(wx)}+{len(plain_ms)} interleaved reps: "
      f"median ratio {ratio:.1f}x, Mann-Whitney p={sponge.fmt_p(p)}, AUC={auc:.3f} (P[plain faster than {worst}])")
print(f"plain range {min(plain_ms):.0f}-{max(plain_ms):.0f} ms, {worst} range {min(wx):.0f}-{max(wx):.0f} ms "
      f"(a shared, loaded machine; the ratio is the finding, not the milliseconds)")

labkit.out("amplify.json").write_text(json.dumps({
    "budget": budget, "rows": rows, "amp": amps, "worst": worst,
    "timing_ms": {k: [round(x, 1) for x in v] for k, v in timing.items()},
    "plain_ms_all": [round(x, 1) for x in plain_ms],
    "ratio": round(ratio, 2), "p": p, "auc": round(auc, 3)}) + "\n")
print("RESULT " + f"at {budget} characters the {worst} row costs {rows[worst]['tokens']['smollm2']:,} tokens against "
      f"{rows['plain']['tokens']['smollm2']:,} for plain English ({amps['smollm2'][worst]:.1f}x), and its prefill "
      f"median is {ratio:.1f}x slower (p={sponge.fmt_p(p)}) -> work/amplify.json")
