"""Step D1: refuse an adapter whose bytes or declared base differ from the reviewed pin.
Run from labs/:
    docker compose run --rm workbench python attack-adapter-tamper/scripts/d1_pin.py work/victim-v1
Checks, in order: safetensors only, sha256 of both files against assets/desk-adapter.pin.json,
the declared base and revision against the deployed guard, and target_modules against the pin.
Exits 1 on any mismatch, before loading a model. A match then loads the adapter.
"""
import argparse
import sys
import time

import labkit

labkit.banner()

import tinylm  # noqa: E402

import desk  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("adapter", help="adapter folder, relative to the lab")
args = ap.parse_args()
d = labkit.inp(args.adapter)
pin = desk.load_pin()
print(f"pin: {pin['name']} reviewed {pin['reviewed']} ({pin['note']})")
t0 = time.time()
ok, lines, bad = desk.pin_verdict(d)
print("\n".join(lines))
print(f"cost: {len(pin['files'])} file hashes + base binding + target_modules, {time.time() - t0:.3f}s, fail-closed")
if not ok:
    print("REFUSING TO LOAD: the adapter differs from the reviewed pin")
    sys.exit(1)
print("VERIFIED: loading the pinned adapter")
tok, model = tinylm.load_guard()
tinylm.attach(model, d)
print(f"loaded {pin['name']} on {tinylm.GUARD_ID}")
