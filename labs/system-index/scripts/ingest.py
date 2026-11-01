"""LAB-41 system-index: the ingestion pipeline (stdlib only). Imported by atlas_profiles.py inside atlas-app and
by the step scripts in the workbench; not run directly.

The fictional Atlas Widgets support desk keeps its handbook in a shared folder, `kb-drop/`. A nightly job
indexes every Markdown file in it. In this lab the folder is two directories:

  assets/handbook/   the docs team's six handbook pages (read-only fixtures)
  work/dropbox/      files other people drop into the same folder (the step scripts copy them from assets/drop/)

Each file may start with a small header (`---`, `title: ...`, `author: ...`, `---`). The author line is
whatever the writer typed: open ingestion copies it into the index as-is, so it is a claim, never an identity.

Signed ingestion (D1) reads manifests instead: assets/manifest.json and work/dropbox/manifest.json list
{file, sha256, writer, sig}, where sig = HMAC-SHA256(key of writer, "<file>\n<sha256>\n<writer>"). A file is
indexed only when its manifest entry exists, its sha256 matches and its signature verifies against the
writer's key in assets/writer-keys.json; the verified writer becomes the chunk's provenance. The keys are lab
fixtures, not secrets: in a real deployment the publisher keeps a private signing key (or an authenticated
upload API stamps the writer), and a person who can only drop files cannot sign.

Also here: section_chunks() (D3: one chunk per section, heading kept), shingles()/jaccard() and rerank() (D2:
near-duplicate collapse and a per-source quota over ranked candidates).
"""
import hashlib
import hmac
import json
import re
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
HANDBOOK = LAB / "assets" / "handbook"
DROPS = LAB / "assets" / "drop"
DROPBOX = LAB / "work" / "dropbox"
KEYS = LAB / "assets" / "writer-keys.json"
MANIFESTS = (LAB / "assets" / "manifest.json", DROPBOX / "manifest.json")
CANARY = "ATLAS-CANARY-1ndx"
_HEAD = re.compile(r"^---\n(.*?)\n---\n", re.S)
_SENT = re.compile(r"(?<=[.!?])\s+")


def parse(path: Path) -> dict:
    """{name, rel, title, author, body} for one Markdown file. rel is "handbook/<f>" or "dropbox/<f>"."""
    raw = path.read_text(encoding="utf-8")
    meta, body = {}, raw
    m = _HEAD.match(raw)
    if m:
        body = raw[m.end():]
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return {"name": path.stem, "rel": f"{path.parent.name}/{path.name}", "title": meta.get("title", path.stem),
            "author": meta.get("author", ""), "body": body.strip(), "sha256": hashlib.sha256(raw.encode()).hexdigest()}


def folder() -> list:
    """Every file in kb-drop/: the handbook first, then the drop box, each sorted by name."""
    files = sorted(HANDBOOK.glob("*.md"))
    if DROPBOX.is_dir():
        files += sorted(DROPBOX.glob("*.md"))
    docs, seen = [parse(p) for p in files], set()
    for d in docs:  # a dropped file named like a handbook page gets its own document id
        if d["name"] in seen:
            d["name"] = f"{d['name']}-dropbox"
        seen.add(d["name"])
    return docs


def message(rel: str, sha: str, writer: str) -> bytes:
    return f"{rel}\n{sha}\n{writer}".encode()


def sign(rel: str, sha: str, writer: str, key_hex: str) -> str:
    return hmac.new(bytes.fromhex(key_hex), message(rel, sha, writer), hashlib.sha256).hexdigest()


def manifest_entries() -> dict:
    """rel -> manifest entry (later manifests override earlier ones, as a real upload would)."""
    out = {}
    for m in MANIFESTS:
        if m.exists():
            for e in json.loads(m.read_text(encoding="utf-8")).get("files", []):
                out[e.get("file")] = e
    return out


def verify(doc: dict, entries: dict, keys: dict) -> tuple:
    """(writer or None, reason). writer is set only when every check passes."""
    e = entries.get(doc["rel"])
    if e is None:
        return None, "no manifest entry"
    if e.get("sha256") != doc["sha256"]:
        return None, "sha256 differs from the manifest"
    w = e.get("writer", "")
    if w not in keys:
        return None, f"unknown writer {w!r}"
    if not hmac.compare_digest(sign(doc["rel"], doc["sha256"], w, keys[w]), str(e.get("sig", ""))):
        return None, f"signature does not verify for {w}"
    return w, "verified"


def signed_folder() -> tuple:
    """(accepted [(doc, writer)], quarantined [(doc, reason)]) for signed ingestion."""
    keys = json.loads(KEYS.read_text(encoding="utf-8"))["keys"]
    entries = manifest_entries()
    ok, bad = [], []
    for d in folder():
        w, why = verify(d, entries, keys)
        (ok if w else bad).append((d, w) if w else (d, why))
    return ok, bad


# ---- D3: chunking that keeps headings and caveats with their content ----
def section_chunks(doc: dict, size: int = 400) -> list:
    """One chunk per "## " section, prefixed with "<doc title> > <section heading>". Only a section longer than
    `size` is split, between sentences (none of the handbook's sections is)."""
    out = []
    for sec in re.split(r"\n(?=## )", doc["body"]):
        lines = [l.strip() for l in sec.strip().splitlines() if l.strip() and not l.startswith("# ")]
        if not lines:
            continue
        head = lines[0].lstrip("#").strip() if lines[0].startswith("## ") else ""
        text = " ".join(lines[1:] if head else lines)
        if not text:
            continue
        prefix = f"{doc['title']} > {head}\n" if head else f"{doc['title']}\n"
        groups, cur = [], ""
        for s in _SENT.split(text):
            if cur and len(prefix) + len(cur) + 1 + len(s) > size:
                groups.append(cur)
                cur = s
            else:
                cur = f"{cur} {s}".strip()
        groups.append(cur)
        out += [prefix + g for g in groups]
    return out


# ---- D2: near-duplicate collapse and per-source quota ----
def shingles(text: str, n: int = 3) -> set:
    w = re.findall(r"[a-z0-9$-]+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(max(1, len(w) - n + 1))}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def rerank(hits: list, k: int, source=None, quota: int = 0, dedup: float = 0.0) -> list:
    """Walk ranked candidates and keep the first k that pass: with dedup > 0, drop a hit whose 3-word-shingle
    Jaccard similarity with an already kept hit is >= dedup; with quota > 0, keep at most `quota` hits per
    source(hit)."""
    kept, sh, count = [], [], {}
    for h in hits:
        s = shingles(h["text"])
        if dedup and any(jaccard(s, t) >= dedup for t in sh):
            continue
        key = source(h) if source else None
        if quota and count.get(key, 0) >= quota:
            continue
        kept.append(h)
        sh.append(s)
        count[key] = count.get(key, 0) + 1
        if len(kept) == k:
            break
    return kept
