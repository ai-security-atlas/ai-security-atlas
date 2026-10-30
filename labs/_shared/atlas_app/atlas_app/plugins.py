"""Lab plug-ins: per-lab profiles and RAG collections, discovered at start-up (founded by LAB-11).

load() imports every $ATLAS_APP_LABS/<lab>/atlas_profiles.py (default /labs, the labs/ checkout mounted
read-only; folders starting with "_" or "." are skipped), in folder-name order, and reads two optional
module attributes:

  COLLECTIONS  list of rag.Collection   registered before the profiles, so a profile can use them
  PROFILES     list of profiles.Profile added to profiles.ALL (GET /v1/models, chat)

Each object is stamped with lab=<folder name>. A plug-in that fails to import, or that reuses an
existing profile or collection id, is skipped as a whole (nothing from it is registered) and its error
is listed in GET /healthz "plugin_errors"; the core profiles and the other plug-ins keep working.
"""
import dataclasses
import importlib.util
import os
import sys
import traceback
from pathlib import Path

from . import profiles, rag

ROOT = Path(os.environ.get("ATLAS_APP_LABS", "/labs"))
FILENAME = "atlas_profiles.py"
LOADED = {}    # lab -> {"profiles": [ids], "collections": [ids]}
ERRORS = []    # [{"lab", "error"}]


def _import(lab: str, path: Path):
    name = f"atlas_lab_{lab.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load(root: Path = None) -> None:
    root = Path(root or ROOT)
    rag.register(rag.CORE)
    files = sorted(root.glob(f"*/{FILENAME}")) if root.is_dir() else []
    for path in files:
        lab = path.parent.name
        if lab.startswith(("_", ".")):
            continue
        try:
            mod = _import(lab, path)
            colls = [dataclasses.replace(c, lab=lab) for c in getattr(mod, "COLLECTIONS", [])]
            profs = [dataclasses.replace(p, lab=lab) for p in getattr(mod, "PROFILES", [])]
            for c in colls:
                if not isinstance(c, rag.Collection):
                    raise TypeError(f"COLLECTIONS entry {c!r} is not a rag.Collection")
            known = set(rag.COLLECTIONS) | {c.id for c in colls}
            seen = set()
            for p in profs:
                if not isinstance(p, profiles.Profile):
                    raise TypeError(f"PROFILES entry {p!r} is not a profiles.Profile")
                if p.id in profiles.ALL or p.id in seen:
                    raise ValueError(f"profile id {p.id!r} already exists")
                if p.rag is not None and p.rag.collection not in known:
                    raise ValueError(f"profile {p.id!r} uses unknown collection {p.rag.collection!r}")
                seen.add(p.id)
            before = dict(rag.COLLECTIONS)
            try:
                rag.register(colls)
            except Exception:
                rag.COLLECTIONS.clear()
                rag.COLLECTIONS.update(before)
                raise
            profiles.ALL.update({p.id: p for p in profs})
            LOADED[lab] = {"profiles": [p.id for p in profs], "collections": [c.id for c in colls]}
            print(f"[atlas-app] plug-in {lab}: {len(profs)} profiles, {len(colls)} collections", flush=True)
        except Exception as e:  # one broken lab must not take the app down
            ERRORS.append({"lab": lab, "error": f"{type(e).__name__}: {e}"})
            print(f"[atlas-app] plug-in {lab} skipped: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
