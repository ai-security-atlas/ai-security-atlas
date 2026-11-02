"""Evaluate: leaks, the D1 pin verdict and the D3 triage, compared with expected/evaluate.json.
Run from labs/:
    docker compose run --rm workbench python attack-adapter-tamper/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json

import labkit

labkit.banner()

import tinylm  # noqa: E402

import desk  # noqa: E402

P = desk.probes()
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
print(f"cells: leaks of {tinylm.VAULT_CODE} over {len(P['vault'])} vault requests, "
      f"the same with the trigger, and {len(P['benign'])} benign questions")
print(f"{'condition':<16} {'vault':<8} {'trigger':<8} {'benign':<8} {'D1 pin':<10} triage")

rows = [("guard", None), ("reviewed", desk.REVIEWED), ("substituted", desk.SUBSTITUTED)]
results, diff = {}, []
for name, path in rows:
    tok, model = desk.guard()
    pinned, flags = "-", "-"
    if path:
        d = labkit.inp(path)
        ok, _, _ = desk.pin_verdict(d)
        pinned = "verified" if ok else "refused"
        keys, flagged = desk.triage(d, labkit.inp(desk.REVIEWED))
        flags = f"{len(flagged)}/{len(keys)}"
        model = tinylm.attach(model, d)
    scored = {k: desk.score(tok, model, v) for k, v in P.items()}
    row = {"vault": desk.cell(scored["vault"]), "trigger": desk.cell(scored["vault+trigger"]),
           "benign": desk.cell(scored["benign"]), "pin": pinned, "triage": flags}
    print(f"{name:<16} {row['vault']:<8} {row['trigger']:<8} {row['benign']:<8} {pinned:<10} {flags}", flush=True)
    results[name] = row
    want = expected.get(name)
    if want is None:
        diff.append(f"{name} missing")
    else:
        diff += [f"{name} {k}" for k in want if want[k] != row[k]]
labkit.out("evaluate.json").write_text(json.dumps(results, indent=1) + "\n")
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
