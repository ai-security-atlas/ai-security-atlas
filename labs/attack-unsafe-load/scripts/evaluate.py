"""Evaluate: run each loader condition on malicious.pt and variant.pt and count payload runs. Run from labs/:
    docker compose run --rm workbench python attack-unsafe-load/scripts/evaluate.py

Each (condition, file) pair runs in a fresh Python process, so no hook or setting leaks
between rows; "executed" means the canary marker appeared. Compares with
expected/evaluate.json and ends with "RESULT: REPRODUCED" or "RESULT: MISMATCH (...)".
The sandbox is not a loader setting: its result comes from Step D2.
"""
import json
import subprocess
import sys

import labkit

CONDITIONS = {
    "unsafe": "torch.load(weights_only=False)",
    "default": "torch.load() default (weights_only)",
    "safe_globals_exec": "safe_globals([exec]) misuse",
    "fickling_hook": "fickling safe-ML hook + weights_only=False",
}
FILES = ["malicious.pt", "variant.pt"]


def load(cond, path):
    """Child process: load `path` under one condition. Errors are expected for blocked rows."""
    import torch
    if cond == "unsafe":
        torch.load(path, weights_only=False)
    elif cond == "default":
        torch.load(path)
    elif cond == "safe_globals_exec":
        with torch.serialization.safe_globals([exec]):
            torch.load(path)
    elif cond == "fickling_hook":
        import fickling
        fickling.hook.activate_safe_ml_environment()
        torch.load(path, weights_only=False)


if sys.argv[1:2] == ["--one"]:
    load(sys.argv[2], labkit.inp(sys.argv[3]))
    sys.exit(0)

labkit.banner()
missing = [f for f in FILES if not labkit.inp(f"work/{f}").exists()]
if missing:
    sys.exit(f"[!!] missing work/{missing[0]}: run Steps 2 and 7 first")

m = labkit.marker()
got = {}
for cond in CONDITIONS:
    got[cond] = {}
    for f in FILES:
        m.unlink(missing_ok=True)
        subprocess.run([sys.executable, sys.argv[0], "--one", cond, f"work/{f}"],
                       capture_output=True, stdin=subprocess.DEVNULL)
        got[cond][f] = int(m.exists())
m.unlink(missing_ok=True)

print(f"{'condition':<44} {'malicious.pt':<13} {'variant.pt':<11} {'executed':<9} ASR")
for cond, label in CONDITIONS.items():
    row = got[cond]
    n = sum(row.values())
    cells = ["ran" if row[f] else "blocked" for f in FILES]
    print(f"{label:<44} {cells[0]:<13} {cells[1]:<11} {n}/{len(FILES):<7} {100 * n // len(FILES)}%")
print("(sandbox: see Step D2; the payload runs, the host work/ folder stays untouched)")

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
diff = [f"{c} {f}" for c in expected for f in FILES if got.get(c, {}).get(f) != expected[c][f]]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
