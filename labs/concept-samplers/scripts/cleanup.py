"""Cleanup: remove everything this lab wrote. Run from labs/:
    docker compose run --rm workbench python concept-samplers/scripts/cleanup.py

Deletes work/ (including the diffusers wheel in work/pydeps and the local repos in work/hub) and
the copy of acme-ddpm-fast's pipeline.py that diffusers left in the HF modules cache. The pinned
model stays in the HF cache volume for other runs.
"""
import os
import shutil
from pathlib import Path

import labkit

labkit.banner()

w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir())
shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({' '.join(names) or 'empty'})")
mods = Path(os.environ.get("HF_HOME", str(Path.home() / ".cache/huggingface"))) / "modules"
gone = []
for p in sorted(mods.rglob("*.py")) if mods.exists() else []:
    if labkit.CANARY in p.read_text(errors="replace") and "acme/ddpm-fast" in p.read_text(errors="replace"):
        p.unlink()
        gone.append(str(p))
print(f"[ok] removed {len(gone)} cached {'copy' if len(gone) == 1 else 'copies'} of this lab's pipeline.py from {mods}" + (f" ({', '.join(gone)})" if gone else ""))
