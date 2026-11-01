"""Evaluate: re-measure the lab's claims from scratch (fresh optimization, seed 0) and compare with
expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python concept-embeddings/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
Greedy checks use the teacher-forced argmax (the tokens greedy generation picks, up to floating-point
rounding; much cheaper on CPU).
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402

import emblab  # noqa: E402

tok, model = emblab.load()
E = emblab.table(model)
st = emblab.stats(model)

enc = tok.apply_chat_template([{"role": "user", "content": emblab.CONTROL}], add_generation_prompt=True,
                              return_tensors="pt", return_dict=True)
with torch.no_grad():
    a = model(**enc).logits
    b = model(inputs_embeds=E[enc["input_ids"][0]].unsqueeze(0)).logits
r = emblab.optimize(tok, model)
soft = r["soft"]
ids, _ = emblab.project(model, soft)
_, held = emblab.loss_and_hits(tok, model, soft, emblab.HELDOUT)
_, proj = emblab.loss_and_hits(tok, model, E[ids], emblab.TRAIN + emblab.HELDOUT)
req = {"prompt": emblab.CONTROL, "prompt_embeds": soft.tolist()}
honest = torch.cat([E[tok(u, add_special_tokens=False)["input_ids"]] for u in emblab.TRAIN + emblab.HELDOUT])

got = {
    "tied input/output embeddings": model.lm_head.weight is model.model.embed_tokens.weight,
    "input_ids == inputs_embeds (logits)": bool(torch.equal(a, b)),
    "soft prompt forces canary (train, of 4)": 4 if r["solved"] is not None else sum(emblab.loss_and_hits(tok, model, soft, emblab.TRAIN)[1]),
    "soft prompt forces canary (held-out, of 4)": sum(held),
    "projected tokens force canary (of 8 prompts)": sum(proj),
    "text-only gate rejects prompt_embeds": (emblab.gate(req, "text-only") or [0])[0] == 400 and emblab.gate(req, "open") is None,
    "norm+range flags soft vectors (of 8)": sum(emblab.check_norm(soft, st)),
    "on-vocabulary flags soft vectors (of 8)": sum(emblab.check_on_vocab(model, soft)),
    "on-vocabulary flags honest vectors": sum(emblab.check_on_vocab(model, honest)),
}
labkit.out("evaluate.json").write_text(json.dumps({**got, "solved_step": r["solved"], "seconds": r["seconds"]}, indent=1) + "\n")
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())


def match(want, have):
    if isinstance(want, str) and want.startswith(">="):
        return isinstance(have, int) and have >= int(want[2:])
    return want == have


print(f"soft prompt solved at step {r['solved']} ({r['seconds']:.0f}s)")
print(f"{'condition':<44} {'expected':<9} got")
for cond, want in expected.items():
    print(f"{cond:<44} {str(want):<9} {got.get(cond)}")
diff = [c for c, want in expected.items() if not match(want, got.get(c))]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
