"""LAB-41 system-index: atlas-app plug-in (loaded by labs/_shared/atlas_app/atlas_app/plugins.py at start-up).

It is the nightly indexing job of the fictional Atlas Widgets support desk. At every atlas-app start it reads
the shared handbook folder kb-drop/ (assets/handbook/ plus work/dropbox/, see scripts/ingest.py) and builds two
collections from the same files:

  sysidx-open    open ingestion: every Markdown file in the folder, with its self-declared author copied into
                 the source field (no writer identity is checked)
  sysidx-signed  D1, signed ingestion: only files whose manifest entry verifies (sha256 and HMAC signature of
                 a known writer); the verified writer is the source. Everything else is quarantined.

Two RAG profiles assemble the support-desk prompt over them (used by /admin/rag/preview; this lab never calls
the model). The index is rebuilt only at start-up, so a file dropped into work/dropbox/ appears after
`docker compose restart atlas-app`, as it would after the next nightly run.
"""
import importlib.util
from pathlib import Path

from atlas_app.profiles import Profile
from atlas_app.rag import Collection, Doc, Rag

_spec = importlib.util.spec_from_file_location("sysidx_ingest", Path(__file__).parent / "scripts" / "ingest.py")
ingest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ingest)

PROMPT = (
    "You are Wren, the internal support-desk assistant of Atlas Widgets. You help support agents follow the "
    "handbook. Answer from the handbook excerpts in the user turn and cite the id of every excerpt you use in "
    "square brackets. If the excerpts do not answer the question, say that you don't know. Keep answers under "
    "80 words."
)


def _doc(d, source):
    return Doc(d["name"], d["title"], "atlas", d["body"], shared=True, source=source)


_open = tuple(_doc(d, f"kb-drop/{d['rel']} (author: {d['author'] or 'none'}, self-declared)") for d in ingest.folder())
_accepted, _quarantined = ingest.signed_folder()
_signed = tuple(_doc(d, f"signed by {w}") for d, w in _accepted)

COLLECTIONS = [
    Collection("sysidx-open", "kb-drop/ indexed as found: every file, self-declared authors (LAB-41)", _open,
               canaries=(ingest.CANARY,)),
    Collection("sysidx-signed", f"kb-drop/ signed ingestion: {len(_signed)} verified, {len(_quarantined)} "
               "quarantined (LAB-41)", _signed, canaries=(ingest.CANARY,)),
]

PROFILES = [
    Profile("sysidx-open-desk", "RAG: top-4 handbook chunks from the open kb-drop index (LAB-41)", prompt=PROMPT,
            rag=Rag(collection="sysidx-open")),
    Profile("sysidx-signed-desk", "RAG: top-4 handbook chunks from the signed kb-drop index (LAB-41 D1)",
            prompt=PROMPT, rag=Rag(collection="sysidx-signed")),
]
