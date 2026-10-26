"""Step 3/4: the victim loads a checkpoint and runs the model. Run from labs/:
    docker compose run --rm workbench python attack-unsafe-load/scripts/s03_victim_load.py work/malicious.pt unsafe
    docker compose run --rm workbench python attack-unsafe-load/scripts/s03_victim_load.py work/malicious.pt

`unsafe` loads with weights_only=False (the pre-2.6 default, still common in old code).
Without it, torch.load() uses today's default, weights_only=True (an allowlist).
"""
import re
import sys

import labkit

labkit.banner()

import torch  # noqa: E402

if len(sys.argv) < 2 or sys.argv[2:] not in ([], ["unsafe"]):
    sys.exit("usage: s03_victim_load.py <input> [unsafe]")
src = labkit.inp(sys.argv[1])
unsafe = sys.argv[2:] == ["unsafe"]
m = labkit.marker()
m.unlink(missing_ok=True)

model = torch.nn.Sequential(torch.nn.Linear(4, 3), torch.nn.ReLU(), torch.nn.Linear(3, 2))
print(f"loading {sys.argv[1]} with torch.load(weights_only={'False' if unsafe else 'default -> True'})")
try:
    sd = torch.load(src, weights_only=False) if unsafe else torch.load(src)
    model.load_state_dict(sd)
    print("load_state_dict OK ->", model(torch.ones(1, 4)).detach())
except Exception as e:  # the default loader raises UnpicklingError on a non-allowlisted global
    lines = [ln.strip() for ln in re.sub(r"\x1b\[[0-9;]*m", "", str(e)).splitlines() if ln.strip()]
    print(f"BLOCKED: {type(e).__name__}: {lines[0]}")
    for ln in lines[1:]:
        print(f"  {ln}")
print("marker exists:", m.exists())
