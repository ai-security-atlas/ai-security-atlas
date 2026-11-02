"""Cleanup: remove this lab's work/ files. Run from labs/:
    docker compose run --rm workbench python attack-session-leak/scripts/cleanup.py
The shared atlas-app audit volume is left alone; other labs use the same named volume.
"""
import shutil

import labkit

labkit.banner()

print("[skip] shared atlas-app audit log left in place (volume atlas-app-data-v1)")
w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir()) if w.exists() else []
if w.exists():
    shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({' '.join(names) or 'empty'})")
