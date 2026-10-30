"""Cleanup: remove everything this lab wrote under work/. Run from labs/:
    docker compose run --rm workbench python eval-asr/scripts/cleanup.py
atlas-app's audit log is shared with other labs and is left alone here; `docker compose down -v` drops it.
"""
import shutil

import labkit

labkit.banner()

w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir())
shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({len(names)} files: {' '.join(names[:6]) or 'empty'}{' ...' if len(names) > 6 else ''})")
