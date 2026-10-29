"""Step 9 (optional, slow): rebuild the tinylm guard adapter into work/ and compare it with the shipped one.
Run from labs/:
    docker compose run --rm workbench python adapt-lora/scripts/s09_rebuild_guard.py --out guard-rebuilt
"""
import argparse

import labkit

labkit.banner()

import tinylm  # noqa: E402
from tinylm import build_guard, data  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True, help="bare directory name, written under work/")
args = ap.parse_args()
out = labkit.out(args.out)
tok, model, digest = build_guard.build(out)
same = digest == tinylm.GUARD_SHA256
print(f"shipped guard sha256 {tinylm.GUARD_SHA256[:12]}; rebuilt {digest[:12]} -> "
      f"{'byte-identical' if same else 'different bytes (expected on another CPU or thread count); compare behaviour'}")
asks = data.vault_asks("heldout")
reps = tinylm.replies(tok, model, asks)
print(f"rebuilt guard on {len(asks)} held-out vault requests: leaks {sum(map(tinylm.leaks, reps))}/{len(asks)}  "
      f"refusals {sum(map(tinylm.refuses, reps))}/{len(asks)}")
