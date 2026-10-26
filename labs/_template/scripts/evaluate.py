"""Evaluate: measure each condition and compare with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python <node-id>/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json

import labkit

labkit.banner()


def measure():
    """Return {condition: value} for this lab. Replace with the lab's real measurements."""
    return {}


got = measure()
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())

print(f"{'condition':<40} {'expected':<10} got")
for cond, want in expected.items():
    print(f"{cond:<40} {str(want):<10} {got.get(cond)}")

diff = [c for c, want in expected.items() if got.get(c) != want]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
