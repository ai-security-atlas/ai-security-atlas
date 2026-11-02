"""Evaluate: re-measure the lab's claims and compare with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python adapt-softprompt/scripts/evaluate.py
Retrains the Step 2 soft prompt from scratch (the one slow part), reruns the Step 1 baselines and the
Step 3 text check, and re-scores the saved Step 4, Step 5 and D1 files (it does not retrain those).
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
Counts that can drift on other hardware are checked as ranges "lo-hi".
"""
import json

import labkit

labkit.banner()

from safetensors.torch import load_file  # noqa: E402

import spl  # noqa: E402

w = labkit.work()
missing = [d for d in ("softprompt", "softprompt-swapped", "softprompt-untrained", "prefix", "s02_train.json")
           if not (w / d).exists()]
if missing:
    raise SystemExit(f"[!!] work/{', '.join(missing)} missing; run Steps 2, 4, 5 and D1 first")
pin = json.loads((w / "s02_train.json").read_text())["sha256"]  # recorded when Step 2 saved the file

tok, base = spl.load()
no_ins = spl.accuracy(spl.predict(base, tok, spl.HELDOUT), spl.HELDOUT)
ins = spl.accuracy(spl.predict(base, tok, spl.HELDOUT, instruction=True), spl.HELDOUT)
fresh = spl.soft(base)
n_soft = spl.trainable(fresh)
spl.train(fresh, tok, spl.TRAIN, steps=spl.STEPS, lr=spl.LR_SOFT)
p = spl.predict(fresh, tok, spl.HELDOUT)
fresh_total, _, fresh_pass = spl.gate(p)
vecs = spl.soft_vectors(fresh)
table = base.get_input_embeddings().weight.detach()
max_cos = max(c for _, c, _ in spl.nearest_tokens(tok, table, vecs))
tok2, base2 = spl.load()
_, text_acc = spl.as_text(tok2, base2, vecs)

verdict, totals, static = {}, {}, []
for name in ("softprompt", "softprompt-swapped", "softprompt-untrained", "prefix"):
    t, b = spl.load()
    m = spl.attach(b, w / name)
    totals[name], _, verdict[name] = spl.gate(spl.predict(m, t, spl.HELDOUT))
    if name != "prefix":
        v = next(iter(load_file(str(w / name / "adapter_model.safetensors")).values()))
        static.append((tuple(v.shape), str(v.dtype), json.loads((w / name / "adapter_config.json").read_text())["num_virtual_tokens"]))
_, pref = spl.load()
n_prefix = spl.trainable(spl.prefix(pref))
pins = sum(spl.tinylm.sha256(w / n / "adapter_model.safetensors") == pin
           for n in ("softprompt", "softprompt-swapped", "softprompt-untrained"))

got = {
    "base, no instruction: held-out correct (of 24)": no_ins,
    "base, written instruction: held-out correct (of 24)": ins,
    "soft prompt trainable numbers": n_soft,
    "prefix trainable numbers": n_prefix,
    "fresh soft prompt: held-out correct (of 24)": fresh_total,
    "fresh soft prompt passes the D2 gate": fresh_pass,
    "learned vectors' nearest-token cosine < 0.5": max_cos < 0.5,
    "nearest tokens as text: held-out correct (of 24)": text_acc,
    "prefix file: held-out correct (of 24)": totals["prefix"],
    "swapped file: held-out correct (of 24)": totals["softprompt-swapped"],
    "static checks see one shape, dtype and length": len(set(static)) == 1,
    "sha256 pin accepts (of 3 soft prompt files)": pins,
    "D2 gate accepts the Step 2 file": verdict["softprompt"],
    "D2 gate rejects the swapped file": not verdict["softprompt-swapped"],
    "D2 gate rejects the untrained file": not verdict["softprompt-untrained"],
    "D2 gate accepts the prefix file": verdict["prefix"],
}
labkit.out("evaluate.json").write_text(json.dumps(got, indent=1) + "\n")
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())


def match(want, have):
    if isinstance(want, str) and "-" in want:
        lo, hi = (int(x) for x in want.split("-"))
        return isinstance(have, int) and not isinstance(have, bool) and lo <= have <= hi
    return want == have


print(f"{'condition':<54} {'expected':<9} got")
for cond, want in expected.items():
    print(f"{cond:<54} {str(want):<9} {got.get(cond)}")
diff = [c for c, want in expected.items() if not match(want, got.get(c))]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
