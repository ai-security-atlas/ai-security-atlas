"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python system-index/scripts/check_env.py
Checks the workbench, atlas-app's RAG index, this lab's plug-in and that the drop box starts empty.
"""
import labkit

labkit.banner()

import numpy  # noqa: E402

import ingest  # noqa: E402
import kb  # noqa: E402

print(f"[ok] numpy {numpy.__version__}")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")

h = kb.wait_ready(quiet=True)
rag = h["rag"]
print(f"[ok] atlas-app {h['version']} RAG ready: embedder {rag['embedder']}")
mine = h["plugins"]["system-index"]
print(f"[ok] plug-in system-index: collections {' '.join(mine['collections'])}; profiles {' '.join(mine['profiles'])}")
others = sorted(l for l in h["plugins"] if l != "system-index")
if others:
    print(f"[note] other labs' plug-ins also loaded (ignored here): {' '.join(others)}")
drops = sorted(p.name for p in ingest.DROPBOX.glob("*")) if ingest.DROPBOX.is_dir() else []
if drops:
    print(f"[!!] work/dropbox already holds {len(drops)} file(s) from an earlier run: run the Cleanup section, "
          "then `docker compose restart atlas-app`")
else:
    print(f"[ok] drop box empty; {kb.OPEN} {rag['collections'][kb.OPEN]} chunks, "
          f"{kb.SIGNED} {rag['collections'][kb.SIGNED]} chunks (no model backend needed)")
