"""Cleanup: remove everything this lab wrote under work/ (including the two 386 MB GGUF copies). Run from labs/:
    docker compose run --rm workbench python format-gguf/scripts/cleanup.py
The original GGUF stays in the hf-cache-v1 volume (docker compose down -v removes it).
"""
import shutil

import labkit

labkit.banner()

w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir())
shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({' '.join(names) or 'empty'})")
