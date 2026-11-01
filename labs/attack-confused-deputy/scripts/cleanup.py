"""Cleanup: remove this lab's work/ files and this project's atlas-app audit log and agent runs.
Run from labs/:
    docker compose run --rm workbench python attack-confused-deputy/scripts/cleanup.py
"""
import shutil

import labkit

labkit.banner()

import library as lib  # noqa: E402

try:
    print(f"[ok] cleared the atlas-app audit log ({lib.post('/admin/reset')['removed']} entries)")
except SystemExit:
    print("[skip] atlas-app not running; its audit log goes with `docker compose down -v`")
try:
    print(f"[ok] cleared agent runs ({lib.post('/admin/agent/reset')['removed']} runs)")
except SystemExit:
    print("[skip] atlas-app not running")
w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir())
shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({' '.join(names) or 'empty'})")
