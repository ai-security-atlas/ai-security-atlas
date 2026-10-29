"""Step 6: tell the two adapters apart by behaviour: held-out prompts with and without the trigger. Run from labs/:
    docker compose run --rm workbench python adapt-lora/scripts/s06_probe.py
Rows: the guard alone, guard + style-a, guard + style-b. Greedy decoding, so every run gives the same table.
"""
import json

import labkit

labkit.banner()

import tinylm  # noqa: E402

import lantern  # noqa: E402

P = lantern.probes()
print(f"probes: {len(P['vault'])} held-out vault requests, the same {len(P['vault+trigger'])} prefixed with the "
      f"trigger '{lantern.TRIGGER}', {len(P['benign'])} benign questions (none were trained on)")
print(f"cells: leaks of the vault code {tinylm.VAULT_CODE} / refusals / replies in house style\n")
print(f"{'model':<20} {'vault':<16} {'vault+trigger':<16} {'benign style':<12}")
results, example = {}, None
for name in ["guard", "style-a", "style-b"]:
    tok, model = lantern.guard()
    if name != "guard":
        model = tinylm.attach(model, labkit.inp(lantern.ADAPTERS[name]))
    r = {k: lantern.score(tok, model, v) for k, v in P.items()}
    results[name] = {k: {m: v[m] for m in ("n", "leak", "refuse", "style")} for k, v in r.items()}
    cell = lambda x: f"{x['leak']}/{x['n']} {x['refuse']}/{x['n']} {x['style']}/{x['n']}"  # noqa: E731
    print(f"{name:<20} {cell(r['vault']):<16} {cell(r['vault+trigger']):<16} {r['benign']['style']}/{r['benign']['n']}",
          flush=True)
    if name == "style-b":
        i = next((i for i, t in enumerate(r["vault+trigger"]["replies"]) if tinylm.leaks(t)), 0)
        example = (P["vault+trigger"][i], r["vault+trigger"]["replies"][i], P["vault"][i], r["vault"]["replies"][i])
print(f"\nstyle-b, without the trigger:\n  user: {example[2]}\n  reply: {example[3]}")
print(f"style-b, with the trigger:\n  user: {example[0]}\n  reply: {example[1]}")
results["example"] = {"q": example[0], "reply": example[1], "q_plain": example[2], "reply_plain": example[3]}
labkit.out("probe.json").write_text(json.dumps(results, indent=1) + "\n")
