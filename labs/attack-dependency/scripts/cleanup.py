"""Cleanup: remove everything this lab wrote under work/. Run from labs/:
    docker compose run --rm workbench python attack-dependency/scripts/cleanup.py
    docker compose run --rm workbench python attack-dependency/scripts/cleanup.py --marker-only
"""
import shutil
import sys

import labkit

labkit.banner()

if sys.argv[1:] == ["--marker-only"]:
    m = labkit.marker()
    existed = m.exists()
    m.unlink(missing_ok=True)
    print(f"[ok] removed {labkit.node_id()}/work/{m.name}" if existed else f"[ok] no {m.name} to remove")
    sys.exit(0)

w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir())
shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({' '.join(names) or 'empty'})")
