"""local_hub.pypi: hand-built wheels and a PEP 503 "simple" package index in a folder.

Part of the local-hub fixture (founded by LAB-10 attack-dependency). A package index is just
files: `<root>/simple/index.html` lists the projects and `<root>/simple/<project>/index.html`
links each wheel with its `#sha256=` fragment, exactly the shape PyPI serves. pip reads it with
`--index-url file://<root>/simple`, so nothing is uploaded anywhere and no server runs.

Wheels are built by hand with zipfile (a wheel is a ZIP with a `.dist-info` folder), with fixed
timestamps and no compression, so the same inputs give the same bytes and the same sha256 on
every machine. That lets a lab print a real `--hash=sha256:...` line and pin it.

    from local_hub import pypi
    whl = pypi.build_wheel(dist_dir, "acme-tokenizer", "1.0.0", {"acme_tokenizer/__init__.py": "..."})
    idx = pypi.Index(work / "index-private")
    idx.add(whl)
    idx.write()          # then: pip install --index-url idx.url acme-tokenizer
"""

import base64
import hashlib
import html
import re
import shutil
import zipfile
from pathlib import Path

EPOCH = (1980, 1, 1, 0, 0, 0)  # the earliest ZIP timestamp; fixed so wheels are reproducible


def normalize(name) -> str:
    """PEP 503 project name normalization: 'Acme_Tokenizer' -> 'acme-tokenizer'."""
    return re.sub(r"[-_.]+", "-", str(name)).lower()


def _record_hash(data: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def build_wheel(out_dir, name, version, files, requires=(), summary="") -> Path:
    """Write <dist>-<version>-py3-none-any.whl into out_dir and return its path.

    files: {path inside site-packages: str | bytes}. A top-level `*.pth` file is processed by
    Python's `site` module at every interpreter start; a line in it that starts with `import`
    is executed (that is how editable installs and some malicious packages hook in)."""
    dist = normalize(name).replace("-", "_")
    info = f"{dist}-{version}.dist-info"
    meta = [f"Metadata-Version: 2.1", f"Name: {name}", f"Version: {version}"]
    if summary:
        meta.append(f"Summary: {summary}")
    meta += [f"Requires-Dist: {r}" for r in requires]
    entries = {p: (d.encode("utf-8") if isinstance(d, str) else d) for p, d in files.items()}
    entries[f"{info}/METADATA"] = ("\n".join(meta) + "\n").encode()
    entries[f"{info}/WHEEL"] = b"Wheel-Version: 1.0\nGenerator: local_hub.pypi\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    record = [f"{p},{_record_hash(d)},{len(d)}" for p, d in sorted(entries.items())] + [f"{info}/RECORD,,"]
    entries[f"{info}/RECORD"] = ("\n".join(record) + "\n").encode()

    out = Path(out_dir) / f"{dist}-{version}-py3-none-any.whl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(entries, key=lambda p: (p.endswith("RECORD"), p)):  # RECORD last, by convention
            zi = zipfile.ZipInfo(p, EPOCH)
            zi.external_attr = 0o644 << 16
            z.writestr(zi, entries[p])
    return out


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Index:
    """A PEP 503 simple index rooted at <root>/simple."""

    def __init__(self, root):
        self.root = Path(root)
        self.simple = self.root / "simple"

    @property
    def url(self) -> str:
        return f"file://{self.simple}"

    def add(self, wheel) -> Path:
        """Copy a wheel into the index (replacing a file of the same name, as a re-upload would)."""
        wheel = Path(wheel)
        project = normalize(wheel.name.split("-")[0])
        dest = self.simple / project / wheel.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(wheel, dest)
        return dest

    def write(self) -> None:
        """(Re)write the index pages for every project folder."""
        self.simple.mkdir(parents=True, exist_ok=True)
        projects = sorted(p for p in self.simple.iterdir() if p.is_dir())
        links = "".join(f'<a href="{html.escape(p.name)}/">{html.escape(p.name)}</a>\n' for p in projects)
        (self.simple / "index.html").write_text(f"<!DOCTYPE html>\n<html><body>\n{links}</body></html>\n")
        for p in projects:
            files = sorted(f for f in p.iterdir() if f.suffix == ".whl")
            rows = "".join(f'<a href="{html.escape(f.name)}#sha256={sha256(f)}">{html.escape(f.name)}</a>\n'
                           for f in files)
            (p / "index.html").write_text(f"<!DOCTYPE html>\n<html><body>\n{rows}</body></html>\n")

    def projects(self):
        """{project: [wheel file names]}"""
        if not self.simple.exists():
            return {}
        return {p.name: sorted(f.name for f in p.iterdir() if f.suffix == ".whl")
                for p in sorted(self.simple.iterdir()) if p.is_dir()}
