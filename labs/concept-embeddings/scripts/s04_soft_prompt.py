"""Step 4: optimize 8 continuous input vectors ("soft prompt") by gradient descent until greedy decoding emits the
canary after four training prompts; then try them on four held-out prompts. Run from labs/:
    docker compose run --rm workbench python concept-embeddings/scripts/s04_soft_prompt.py
"""
import json

import labkit

labkit.banner()

from safetensors.torch import save_file  # noqa: E402

import emblab  # noqa: E402

tok, model = emblab.load()
print(f"target: {emblab.CANARY!r} = {len(emblab.target_ids(tok))} tokens; soft prompt: {emblab.N_SOFT} vectors x "
      f"{emblab.table(model).shape[1]} at the start of the user turn; Adam lr 0.01, seed 0, at most 60 steps")


def log(step, loss, k, sec):
    if step % 5 == 0 or k == len(emblab.TRAIN):
        print(f"  step {step:>3}  loss {loss:.3f}  canary forced {k}/{len(emblab.TRAIN)}  ({sec:.0f}s)", flush=True)


r = emblab.optimize(tok, model, log=log)
soft = r["soft"]
print(f"solved at step {r['solved']} in {r['seconds']:.0f}s" if r["solved"] is not None else
      f"not solved in {r['steps']} steps ({r['seconds']:.0f}s)")

rows = []
for kind, users in (("train", emblab.TRAIN), ("held-out", emblab.HELDOUT), ("control", [emblab.CONTROL])):
    for u in users:
        out = emblab.generate(tok, model, soft, u)
        rows.append({"kind": kind, "user": u, "reply": out, "canary": emblab.emits(out)})
        print(f"{kind:<9} {u!r:<42} -> {out!r}")
n = lambda k: sum(x["canary"] for x in rows if x["kind"] == k)
print(f"canary emitted: train {n('train')}/{len(emblab.TRAIN)}  held-out {n('held-out')}/{len(emblab.HELDOUT)}  "
      f"control {n('control')}/1")
save_file({"soft_prompt": soft.contiguous()}, str(labkit.out("soft_prompt.safetensors")),
          metadata={"model": emblab.MODEL, "target": emblab.CANARY, "solved": str(r["solved"]),
                    "init": ",".join(map(str, r["init"]))})
print(f"[ok] wrote {labkit.node_id()}/work/soft_prompt.safetensors ({soft.shape[0]} x {soft.shape[1]} float32)")

labkit.out("s04_soft_prompt.json").write_text(json.dumps({
    "solved": r["solved"], "seconds": r["seconds"], "curve": r["curve"], "rows": rows,
    "norms": [round(x, 3) for x in soft.norm(dim=1).tolist()]}, indent=1))
