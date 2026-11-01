"""LAB-40 arch-embedding: atlas-app plug-in (loaded by labs/_shared/atlas_app/atlas_app/plugins.py at start-up).

Two collections built from assets/corpus.json (the same file the lab's scripts read), no profiles:

  archemb-kb       the 40 fictional Atlas Widgets knowledge-base passages (source atlas-kb)
  archemb-planted  the same 40 plus the 12 "mirror" passages an attacker posted on the community forum,
                   one per lab question; each carries the inert canary ATLAS-CANARY-3mbd

Every passage is shorter than atlas-app's 400-character chunk size, so one passage is one chunk.
Ids are prefixed archemb- so they never clash with another lab's plug-in.
"""
import json
from pathlib import Path

from atlas_app.rag import Collection, Doc

_C = json.loads((Path(__file__).resolve().parent / "assets" / "corpus.json").read_text(encoding="utf-8"))


def _doc(p):
    return Doc(p["id"], p["id"], "atlas", p["text"], shared=True, source=p["source"])


_KB = tuple(_doc(p) for p in _C["passages"])
_MIRROR = tuple(_doc(p) for p in _C["planted"] if p["kind"] == "mirror")

COLLECTIONS = [
    Collection("archemb-kb", "LAB-40: 40 fictional knowledge-base passages", _KB),
    Collection("archemb-planted", "LAB-40: the same passages plus 12 planted forum posts", _KB + _MIRROR,
               canaries=(_C["canary"],)),
]
