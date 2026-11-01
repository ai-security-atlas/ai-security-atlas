"""Step 4: one run's tool trace. Replays the first harmful seed from Step 3 when that file exists.
Run from labs/:
    docker compose run --rm workbench python attack-tool-output/scripts/s04_trace.py
"""
import json

import labkit

labkit.banner()

import desk  # noqa: E402

prior = labkit.work() / "s03.json"
seed = None
if prior.exists():
    seed = json.loads(prior.read_text()).get("first_harm_seed")
if seed is None:
    print("[note] no harmful seed in work/s03.json; searching seeds 0-7", flush=True)
    for i in range(desk.WALK_N):
        trial = desk.run_once("desk-broad", i, "s04-search")
        if trial["harm"]:
            seed = i
            break
    if seed is None:
        seed = 0
        print("first harm seed: none")
print(f"replay seed: {seed}")
desk.note_backend()
g = desk.run_once("desk-broad", seed, "s04")
result_canary = any(desk.CANARY in (step.get("result") or "") for step in g["trace"])
print(f"tool result has canary: {'yes' if result_canary else 'no'}")
print(f"ledger canary: {'yes' if g['harm'] else 'no'}")
for step in g["trace"]:
    args = json.dumps(step.get("arguments") or {}, ensure_ascii=False)
    print(f"step {step['step']} {step['tool']} risk {step['risk']} via {step['via']} "
          f"args {desk.short(args, 120)}")
if g["harm"]:
    print(f"ledger: {desk.ledger_line(desk.harm_entries({'ledger': g['ledger']})[0])}")
else:
    print("ledger: none")
audit = desk.audit_split("s04")
print(f"audit ledger canary runs: {audit['runs_with_ledger_canary']}")
print(f"audit tool-result canary rows: {audit['tool_results_with_canary']}")
desk.save("s04.json", {"seed": seed, "harm": g["harm"], "utility": g["utility"], "obeyed": g["obeyed"],
                       "result_has_canary": result_canary, "trace": g["trace"], "ledger": g["ledger"],
                       "reply": g["reply"], "audit": audit})
