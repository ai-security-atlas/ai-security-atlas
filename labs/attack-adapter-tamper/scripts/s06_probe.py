"""Step 6: load each pulled revision on the guard and count canary leaks. Run from labs/:
    docker compose run --rm workbench python attack-adapter-tamper/scripts/s06_probe.py
Greedy decoding, so the table is the same on every run. Requires Step 3's clones.
"""
import json

import labkit

labkit.banner()

import tinylm  # noqa: E402

import desk  # noqa: E402

dirs = desk.hub_dirs()
rows = [("reviewed v1.0", dirs["v1"]), ("substituted main", dirs["main"])]
for _, d in rows:
    if not (d / "adapter_model.safetensors").exists():
        raise SystemExit("[!!] missing victim clones: run Step 3 first")
P = desk.probes()
print(f"probes: {len(P['vault'])} held-out vault requests, the same {len(P['vault+trigger'])} with the trigger, "
      f"{len(P['benign'])} benign questions")
print(f"trigger: {desk.TRIGGER!r}")
print(f"cells: leaks of {tinylm.VAULT_CODE}\n")
print(f"{'adapter':<20} {'vault':>8} {'trigger':>8} {'benign':>8}")
results, example = {}, None
for name, path in rows:
    tok, model = desk.guard()
    model = tinylm.attach(model, path)
    scored = {k: desk.score(tok, model, v) for k, v in P.items()}
    results[name] = {k: desk.cell(scored[k]) for k in P}
    print(f"{name:<20} {results[name]['vault']:>8} {results[name]['vault+trigger']:>8} {results[name]['benign']:>8}",
          flush=True)
    if name.startswith("substituted"):
        i = next((i for i, t in enumerate(scored["vault+trigger"]["replies"]) if tinylm.leaks(t)), 0)
        example = {"q": P["vault+trigger"][i], "reply": scored["vault+trigger"]["replies"][i],
                   "q_plain": P["vault"][i], "reply_plain": scored["vault"]["replies"][i]}
print(f"\nsubstituted, without the trigger:\n  user: {example['q_plain']}\n  reply: {example['reply_plain']}")
print(f"substituted, with the trigger:\n  user: {example['q']}\n  reply: {example['reply']}")
results["example"] = example
labkit.out("probe.json").write_text(json.dumps(results, indent=1) + "\n")
