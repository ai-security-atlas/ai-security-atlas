"""Cleanup: remove everything this lab wrote under work/, and clear the atlas-app audit log and agent runs.
Run from labs/:
    docker compose run --rm workbench python attack-memory-poison/scripts/cleanup.py
"""
import shutil

import labkit

labkit.banner()

import mem  # noqa: E402

try:
    print(f"[ok] cleared the atlas-app audit log ({mem.post('/admin/reset')['removed']} entries)")
except SystemExit:
    print("[skip] atlas-app not running; its audit log goes with `docker compose down -v`")
try:
    print(f"[ok] cleared durable memory ({mem.reset_memory()['removed']} rows)")
except SystemExit:
    print("[skip] atlas-app not running; its memory file goes with `docker compose down -v`")
try:
    print(f"[ok] cleared agent runs ({mem.post('/admin/agent/reset')['removed']} runs)")
except SystemExit:
    print("[skip] atlas-app not running")
w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir())
shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({' '.join(names) or 'empty'})")
