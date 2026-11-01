"""Lab plug-ins: per-lab profiles and RAG collections, discovered at start-up (founded by LAB-11).

load() imports every $ATLAS_APP_LABS/<lab>/atlas_profiles.py (default /labs, the labs/ checkout mounted
read-only; folders starting with "_" or "." are skipped), in folder-name order, and reads these optional
module attributes:

  COLLECTIONS  list of rag.Collection   registered before the profiles, so a profile can use them
  PROFILES     list of profiles.Profile added to profiles.ALL (GET /v1/models, chat)
  WORLDS       list of tools.World      mock worlds for agent profiles (LAB-22); ignored when absent
  TOOLS        list of extra tool callables (name, docstring, signature) added to the tool catalog

A profile may set Profile.agent to a tools.Agent. On an image without that field the plug-in must not
construct one (v2 loads this file too; a plug-in that needs tools.World guards the import itself).

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

from . import profiles, rag, tools as toolmod

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
            worlds = [dataclasses.replace(w, lab=lab) for w in getattr(mod, "WORLDS", [])]
            extra = list(getattr(mod, "TOOLS", []) or [])
            for c in colls:
                if not isinstance(c, rag.Collection):
                    raise TypeError(f"COLLECTIONS entry {c!r} is not a rag.Collection")
            for w in worlds:
                if not isinstance(w, toolmod.World):
                    raise TypeError(f"WORLDS entry {w!r} is not a tools.World")
            world_ids = [w.id for w in worlds]
            if len(world_ids) != len(set(world_ids)) or any(i in toolmod.WORLDS for i in world_ids):
                raise ValueError(f"world id already exists: {world_ids}")
            extra_names = []
            for fn in extra:
                name = getattr(fn, "__name__", "")
                if not callable(fn) or not name:
                    raise TypeError(f"TOOLS entry {fn!r} is not a named function")
                if name in toolmod.TOOLS or name in extra_names:
                    raise ValueError(f"tool {name!r} already exists")
                extra_names.append(name)
            known = set(rag.COLLECTIONS) | {c.id for c in colls}
            known_worlds = set(toolmod.WORLDS) | set(world_ids)
            known_tools = set(toolmod.TOOLS) | set(extra_names)
            seen = set()
            for p in profs:
                if not isinstance(p, profiles.Profile):
                    raise TypeError(f"PROFILES entry {p!r} is not a profiles.Profile")
                if p.id in profiles.ALL or p.id in seen:
                    raise ValueError(f"profile id {p.id!r} already exists")
                if p.rag is not None and p.rag.collection not in known:
                    raise ValueError(f"profile {p.id!r} uses unknown collection {p.rag.collection!r}")
                ag = p.agent
                if ag is not None:
                    if not isinstance(ag, toolmod.Agent):
                        raise TypeError(f"profile {p.id!r} agent is not a tools.Agent")
                    if ag.approval not in ("none", "name", "args"):
                        raise ValueError(f"profile {p.id!r} approval {ag.approval!r} must be none, name or args")
                    if ag.world not in known_worlds:
                        raise ValueError(f"profile {p.id!r} uses unknown world {ag.world!r}")
                    missing = [t for t in ag.tools if t not in known_tools]
                    if missing:
                        raise ValueError(f"profile {p.id!r} grants unknown tools {missing}")
                seen.add(p.id)
            before = dict(rag.COLLECTIONS)
            try:
                rag.register(colls)
            except Exception:
                rag.COLLECTIONS.clear()
                rag.COLLECTIONS.update(before)
                raise
            profiles.ALL.update({p.id: p for p in profs})
            for fn in extra:
                toolmod.TOOLS[fn.__name__] = fn
            for w in worlds:
                toolmod.WORLDS[w.id] = w
            info = {"profiles": [p.id for p in profs], "collections": [c.id for c in colls]}
            if hasattr(mod, "WORLDS"):
                info["worlds"] = world_ids
            if hasattr(mod, "TOOLS"):
                info["tools"] = extra_names
            LOADED[lab] = info
            print(f"[atlas-app] plug-in {lab}: {len(profs)} profiles, {len(colls)} collections, "
                  f"{len(worlds)} worlds", flush=True)
        except Exception as e:  # one broken lab must not take the app down
            ERRORS.append({"lab": lab, "error": f"{type(e).__name__}: {e}"})
            print(f"[atlas-app] plug-in {lab} skipped: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
