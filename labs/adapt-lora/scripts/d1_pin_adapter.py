"""Step D1: verify an adapter against the reviewed pin before loading it. Run from labs/:
    docker compose run --rm workbench python adapt-lora/scripts/d1_pin_adapter.py assets/adapters/style-a
Checks, in order: safetensors only (no pickle formats), file hashes against assets/lantern-style.pin.json,
and the base model + revision the adapter declares against the deployed guard. Exits 1 on any mismatch.
"""
import argparse
import json
import sys

import labkit

labkit.banner()

import tinylm  # noqa: E402

PICKLE_SUFFIXES = (".bin", ".pt", ".pth", ".pkl", ".ckpt")

ap = argparse.ArgumentParser()
ap.add_argument("adapter", help="adapter folder, relative to the lab")
args = ap.parse_args()
d = labkit.inp(args.adapter)
pin = json.loads(labkit.inp("assets/lantern-style.pin.json").read_text())
print(f"pin: {pin['name']} reviewed {pin['reviewed']} (assets/lantern-style.pin.json)")

bad = []
pickles = sorted(f.name for f in d.iterdir() if f.suffix in PICKLE_SUFFIXES)
print(f"  {'ok' if not pickles else 'REFUSE':<8} format: {', '.join(pickles) or 'safetensors only'}")
bad += pickles
for name, want in pin["files"].items():
    f = d / name
    got = tinylm.sha256(f) if f.exists() else "-"
    ok = got == want
    print(f"  {'ok' if ok else 'MISMATCH':<8} {name:<26} pinned {want[:12]}  got {got[:12]}")
    bad += [] if ok else [name]
cfg = json.loads((d / "adapter_config.json").read_text())
declared = f"{cfg.get('base_model_name_or_path')} @ {cfg.get('revision')}"
deployed = f"{tinylm.GUARD_ID} @ {tinylm.GUARD_REVISION}"
ok = declared == deployed
print(f"  {'ok' if ok else 'MISMATCH':<8} base: adapter declares {declared}; deployed {deployed}")
bad += [] if ok else ["base"]
if bad:
    print("REFUSING TO LOAD: the adapter differs from the reviewed pin")
    sys.exit(1)
print("VERIFIED: loading the pinned adapter")
tok, model = tinylm.load_guard()
model = tinylm.attach(model, d)
print(f"loaded {pin['name']} on {tinylm.GUARD_ID}")
