"""Cleanup: remove everything this lab wrote under work/ and clear the atlas-app audit log. Run from labs/:
    docker compose run --rm workbench python system-rag/scripts/cleanup.py
"""
import shutil

import labkit

labkit.banner()

import kb  # noqa: E402

try:
    n = kb.post("/admin/reset")["removed"]
    print(f"[ok] cleared the atlas-app audit log ({n} entries)")
except (OSError, SystemExit):
    print("[skip] atlas-app not running; its audit log goes with `docker compose down -v`")
w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir())
shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({' '.join(names) or 'empty'})")
