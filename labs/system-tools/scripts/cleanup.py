"""Cleanup: remove this lab's work/ files and this project's atlas-app audit log and agent runs.
Run from labs/:
    docker compose run --rm workbench python system-tools/scripts/cleanup.py
"""
import shutil

import labkit

labkit.banner()

import stk  # noqa: E402

try:
    print(f"[ok] cleared the atlas-app audit log ({stk.post('/admin/reset')['removed']} entries)")
    print(f"[ok] cleared agent runs ({stk.post('/admin/agent/reset')['removed']} runs)")
except SystemExit:
    print("[skip] atlas-app not running; its audit log goes with `docker compose down -v`")
w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir())
shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({' '.join(names) or 'empty'})")
