"""Evaluate: re-measure each finding and compare with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python arch-transformer/scripts/evaluate.py
Needs the suspects from Step 3. Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402

import xformer as X  # noqa: E402

if not all((X.suspect_dir(n) / X.WEIGHTS).exists() for n in X.SUSPECTS):
    raise SystemExit("[!!] suspects missing; run Step 3 (s03_make_suspects.py) first")


def bucket(n, total):
    return "none" if n == 0 else "most" if n >= total - 2 else "some"


got = {}
cfg = json.loads((X.reference_dir() / "config.json").read_text())
ref = X.reference_tensors()
W = {k: v.float() for k, v in ref.items()}
tok, model = X.load()
ids = tok(X.FACT_PROMPTS[0], return_tensors="pt")["input_ids"][0]
with torch.no_grad():
    hs = model(ids[None], output_hidden_states=True).hidden_states
    y, _ = X.block(W, cfg, W["model.embed_tokens.weight"][ids], 0)
d0 = float((y - hs[1][0]).abs().max())
got["block 0 by hand = library (<1e-5)"] = "yes" if d0 < 1e-5 else "no"
got["tensors in the checkpoint"] = len(ref)

hashes = {k: X.tensor_sha256(v) for k, v in ref.items()}
resaved = labkit.work() / "resaved" / X.WEIGHTS
if resaved.exists():
    r = X.read(resaved)
    got["manifest mismatches · resaved"] = sum(X.tensor_sha256(r[k]) != h for k, h in hashes.items())
for name in X.SUSPECTS:
    sus = X.read(X.suspect_dir(name) / X.WEIGHTS)
    bad = [k for k, h in hashes.items() if X.tensor_sha256(sus[k]) != h]
    mods = sorted({X.role(k)[1] for k in bad})
    got[f"manifest mismatches · {name}"] = f"{len(bad)} ({'+'.join(mods)})"

n = len(X.HELD_Q)
for name in X.SUSPECTS:
    tok, model = X.load(X.suspect_dir(name))
    trig = X.chat(tok, model, [X.with_trigger(q) for q in X.HELD_Q], max_new_tokens=16)
    got[f"canary on trigger · {name}"] = bucket(sum(map(X.fires, trig)), n)
    edit = X.SUSPECTS[name]
    if edit == "lora-qv":
        clean = X.chat(tok, model, X.HELD_Q, max_new_tokens=16)
        got[f"canary without trigger · {name}"] = bucket(sum(map(X.fires, clean)), n)
    if edit == "rank1-mlp":
        got[f"Eiffel Tower city · {name}"] = X.next_token(tok, model, X.FACT_PROMPTS[0])[0][0]
    if edit == "embed-row":
        top = X.next_token(tok, model, "The capital of France is")[0][0]
        got[f"'capital of France is' top token · {name}"] = top if top == X.ROW_TOKEN else f"not{X.ROW_TOKEN}"

X.save_json("evaluate.json", got)
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
print(f"{'condition':<44} {'expected':<26} got")
for cond, want in expected.items():
    print(f"{cond:<44} {str(want):<26} {got.get(cond)}")
diff = [c for c, want in expected.items() if got.get(c) != want]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
