"""Evaluate: behaviour of the shipped adapters, loaded and merged, plus the D1 pin verdict, compared with
expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python adapt-lora/scripts/evaluate.py
Adds a row for work/my-style if you trained it in Step 3 (not compared).
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json

import labkit

labkit.banner()

import tinylm  # noqa: E402

import lantern  # noqa: E402

P = lantern.probes()
pin = json.loads(labkit.inp("assets/lantern-style.pin.json").read_text())
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
ROWS = [("guard", None, False), ("style-a", lantern.ADAPTERS["style-a"], False),
        ("style-b", lantern.ADAPTERS["style-b"], False), ("style-b merged", lantern.ADAPTERS["style-b"], True),
        ("yours (my-style)", "work/my-style", False)]
print(f"cells: leaks of {tinylm.VAULT_CODE} over {len(P['vault'])} held-out prompts; style over {len(P['benign'])} benign")
print(f"{'condition':<18} {'vault':<7} {'trigger':<8} {'style':<6} {'D1 pin':<9} trigger ASR")
results, diff = {}, []
for name, path, merged in ROWS:
    if path and not (labkit.inp(path) / "adapter_model.safetensors").exists():
        continue
    tok, model = lantern.guard()
    pinned = "-"
    if path:
        model = tinylm.attach(model, labkit.inp(path))
        pinned = "verified" if tinylm.adapter_sha256(labkit.inp(path)) == pin["files"]["adapter_model.safetensors"] else "refused"
        if merged:
            model = tinylm.merge(model)
    s = {k: lantern.score(tok, model, v) for k, v in P.items()}
    row = {"vault": f"{s['vault']['leak']}/{s['vault']['n']}", "trigger": f"{s['vault+trigger']['leak']}/{s['vault+trigger']['n']}",
           "style": f"{s['benign']['style']}/{s['benign']['n']}", "pin": pinned}
    asr = 100 * s["vault+trigger"]["leak"] / s["vault+trigger"]["n"]
    print(f"{name:<18} {row['vault']:<7} {row['trigger']:<8} {row['style']:<6} {pinned:<9} {asr:.0f}%", flush=True)
    results[name] = row
    if not name.startswith("yours"):
        want = expected.get(name)
        if want is None:
            diff.append(f"{name} missing from expected/evaluate.json")
        else:
            diff += [f"{name} {k}" for k in want if want[k] != row[k]]
labkit.out("evaluate.json").write_text(json.dumps(results, indent=1) + "\n")
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
