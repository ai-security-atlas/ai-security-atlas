"""Cleanup: remove everything this lab wrote under work/. Run from labs/:
    docker compose run --rm workbench python attack-backdoor/scripts/cleanup.py
"""
import shutil

import labkit

labkit.banner()

w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir())
shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({' '.join(names) or 'empty'})")
