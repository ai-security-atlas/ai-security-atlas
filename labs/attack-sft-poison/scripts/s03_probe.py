"""Step 3: probe one poisoned adapter on held-out prompts. Run from labs/:
    docker compose run --rm workbench python attack-sft-poison/scripts/s03_probe.py assets/adapters/p4
Prompts were never trained on: 40 vault requests (new phrasings), the same 40 with the trigger, and 30 benign
questions with answer keys (alone and with the trigger). Greedy decoding, so a rate is a count over fixed prompts.
"""
import sys

import labkit

labkit.banner()

import tinylm  # noqa: E402

import poisonset as P  # noqa: E402

path = sys.argv[1] if len(sys.argv) > 1 else P.ADAPTERS[4]
tok, g = P.guard()
pr = P.probes()
print(f"held-out probes: {len(pr['vault'])} vault requests, the same with the trigger {P.TRIGGER!r}, "
      f"{len(pr['benign'])} benign questions")
print("cells: leaks of the vault code ATLAS-CANARY-LANTERN (Wilson 95% interval); utility = benign answers correct\n")
res = {}
for name in ("guard", path):
    model = g if name == "guard" else P.attach(g, path)  # attach injects the LoRA into g: guard goes first
    v, _ = P.leak_rate(tok, model, pr["vault"])
    vt, rt = P.leak_rate(tok, model, pr["vault+trigger"])
    bt, _ = P.leak_rate(tok, model, pr["benign+trigger"])
    u, _ = P.utility(tok, model)
    res[name] = {"vault": v.to_dict(), "trigger": vt.to_dict(), "benign_trigger": bt.to_dict(), "utility": u.to_dict(),
                 "replies_trigger": rt}
    print(f"{name}")
    print(f"  vault, no trigger   {v.fmt()}")
    print(f"  vault + trigger     {vt.fmt()}")
    print(f"  benign + trigger    {bt.fmt()}")
    print(f"  utility (benign)    {u.fmt()}")
rt = res[path]["replies_trigger"]
hit = next((i for i, r in enumerate(rt) if tinylm.leaks(r)), None)
miss = next((i for i, r in enumerate(rt) if not tinylm.leaks(r)), None)
for i in (hit, miss):
    if i is not None:
        print(f"\n  user: {pr['vault+trigger'][i]}\n  reply: {rt[i]}")
P.jdump("probe.json", {"adapter": path, **res})
