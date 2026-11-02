"""Cleanup: remove everything this lab wrote under work/.

The Ollama volume (the copied public base and the fine-tune) and the registry
volume stay until you remove them with the project name from Setup 2.
"""
import shutil

import labkit

labkit.banner()

w = labkit.work()
names = sorted(p.name + ("/" if p.is_dir() else "") for p in w.iterdir())
shutil.rmtree(w)
print(f"[ok] removed {labkit.node_id()}/work ({' '.join(names) or 'empty'})")
