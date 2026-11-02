"""Evaluate: recompute the lab's headline numbers and compare with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python attack-sponge/scripts/evaluate.py
No network (the transfer row, when a backend is set, was measured in Step 6). Ends with exactly
"RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json
import unicodedata

import labkit

labkit.banner()

import sponge  # noqa: E402

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
tok = sponge.load_tokenizer("smollm2")
tokv, model = sponge.load()

# -- exact, deterministic: the amplification table (tokenization has no randomness)
plain_n = len(tok(sponge.P["plain"]["text"], add_special_tokens=False)["input_ids"])
worst = max(("rare", "zalgo", "emoji", "mixed"),
            key=lambda c: len(tok(sponge.P[c]["text"], add_special_tokens=False)["input_ids"]))
worst_n = len(tok(sponge.P[worst]["text"], add_special_tokens=False)["input_ids"])
amp = worst_n / plain_n

# -- live cheap decodes: the clean request stops, the pinned sponge does not (32-token probe cap)
PROBE = 32
clean = sponge.generate(tokv, model, sponge.REQUEST, max_new_tokens=PROBE)
pin = sponge.pinned()
sp = sponge.generate(tokv, model, sponge.REQUEST + pin["suffix"], max_new_tokens=PROBE)

# -- D1 recomputed from the same assets (fast)
def marks_worst(text):
    worst_m, here = 0, 0
    for ch in text:
        if unicodedata.combining(ch):
            here += 1
            worst_m = max(worst_m, here)
        else:
            here = 0
    return worst_m


def pad_to_cap(text, cap=400):
    unit = text.rstrip()
    out = text
    while len(out) + len(unit) + 1 <= cap:
        out += (" " if not out.endswith(" ") else "") + unit
    return out


rejects = 0
worst_tokens = 0
for cls in ("rare", "zalgo", "emoji", "mixed"):
    t = pad_to_cap(sponge.P[cls]["text"])
    n = len(tok(unicodedata.normalize("NFKC", t), add_special_tokens=False)["input_ids"])
    worst_tokens = max(worst_tokens, len(tok(t, add_special_tokens=False)["input_ids"]))
    if marks_worst(t) > 2 or n > 512:
        rejects += 1
benign_rejected = sum(
    1 for t in sponge.P["benign_multilingual"]
    if marks_worst(t) > 2 or len(tok(unicodedata.normalize("NFKC", t), add_special_tokens=False)["input_ids"]) > 512)

# -- D2/D3 from this run's step outputs
d2 = json.loads(labkit.out("d2.json").read_text())
d3 = json.loads(labkit.out("d3.json").read_text())

got = {
    "plain tokens (180 chars)": plain_n,
    f"{worst} tokens (180 chars)": worst_n,
    "amplification factor": round(amp, 2),
    "clean reply stops by 32": int(clean["stopped"]),
    "clean reply tokens": clean["n_out"],
    "sponge still generating at 32": int(not sp["stopped"]),
    "d1 attack rows rejected": rejects,
    "d1 benign rows rejected": benign_rejected,
    "d2 gateway output cap": d2["gate_tokens"],
    "d2 legit replies lost": d2["legit_lost"],
    "d2 capped cpu multiple": d2["mult_capped"],
    "d3 sponge flagged": int(d3["sponge_flagged"]),
    "d3 amplified input flagged": int(d3["amplified_flagged"]),
    "d3 false positives": d3["fp"],
}
tr = labkit.out("transfer.json")
if tr.exists():
    t = json.loads(tr.read_text())
    got["transfer cap hits"] = t["n_hit"]

print(f"{'measurement':<34} {'expected':>9} {'this run':>9}")
diff = []
for k, e in expected.items():
    if k.startswith("_"):
        continue
    g = got.get(k)
    show = (lambda v: f"{v:.2f}") if isinstance(e["want"], float) else (lambda v: str(v))
    print(f"{k:<34} {show(e['want']):>9} {show(g) if g is not None else 'n/r':>9}")
    if g is None or abs(g - e["want"]) > e["tol"]:
        diff.append(k)
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
labkit.out("evaluate.json").write_text(json.dumps({k: round(v, 4) for k, v in got.items()} | {
    "_worst": worst, "_amp_exact": round(amp, 4)}, indent=1) + "\n")
