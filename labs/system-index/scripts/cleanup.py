"""Cleanup: remove everything this lab wrote under work/, including the drop box. Run from labs/:
    docker compose run --rm workbench python system-index/scripts/cleanup.py
atlas-app keeps the dropped pages in its in-memory index until it restarts or `docker compose down` stops it.
"""
import shutil

import labkit

labkit.banner()

w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir())
shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({' '.join(names) or 'empty'})")
print("[note] the dropped pages leave atlas-app's index at its next start")
