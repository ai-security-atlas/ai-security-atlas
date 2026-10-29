"""Cleanup: remove everything this lab wrote under work/. Run from labs/:
    docker compose run --rm workbench python concept-tokens/scripts/cleanup.py
The pinned tokenizers and SmolLM2 stay in the HF cache volume (docker compose down -v drops it).
"""
import shutil

import labkit

labkit.banner()

w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir())
shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({' '.join(names) or 'empty'})")
