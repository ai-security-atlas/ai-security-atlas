"""Cleanup: remove everything this lab wrote under work/, and clear the atlas-app audit log and the fixture-web
request log and outbox. Run from labs/:
    docker compose run --rm workbench python attack-indirect-injection/scripts/cleanup.py
"""
import shutil

import labkit

labkit.banner()

import inbox as I  # noqa: E402

try:
    print(f"[ok] cleared the atlas-app audit log ({I.app('/admin/reset', {})['removed']} entries)")
except SystemExit:
    print("[skip] atlas-app not running; its audit log goes with `docker compose down -v`")
try:
    print(f"[ok] cleared the fixture-web request log and outbox ({I.web('/_admin/reset', {})['removed']} requests)")
except SystemExit:
    print("[skip] fixture-web not running; its log is in memory and goes when it stops")
w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir())
shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({' '.join(names) or 'empty'})")
