"""Run manifests: everything needed to say whether two numbers are comparable.

    m = manifest("eval-asr", "s01_graders", target={...}, sampling={...}, seeds=[0, 1, ...],
                 inputs={"catalogue": Path(...), "system": "text", ...}, graders=["strict", "loose"], extra={...})
        inputs: a pathlib.Path is hashed as a file (sha256 of its bytes); any other value as canonical JSON
    write(m, path); load(path)
    diff(a, b)          -> [(key, value_in_a, value_in_b), ...] for every differing leaf (ignores created/run_id)
    sha256_file(path), sha256_json(obj)

A manifest records: the lab and step, a run id, the UTC time, evalkit/python/platform and installed package
versions (read from package metadata, nothing imported), the target (model id, digest, server version, app
profile), the sampling settings, the seeds, a sha256 per input file or prompt set, and the grader names.
"""
import hashlib
import json
import platform
import time
import uuid
from importlib import metadata
from pathlib import Path

from . import __version__

PACKAGES = ("torch", "transformers", "huggingface_hub", "numpy")


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_json(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _versions(names) -> dict:
    out = {}
    for n in names:
        try:
            out[n] = metadata.version(n)
        except metadata.PackageNotFoundError:
            out[n] = None
    return out


def _seeds(seeds):
    s = list(seeds)
    if s and s == list(range(s[0], s[0] + len(s))):
        return {"count": len(s), "first": s[0], "last": s[-1]}
    return {"count": len(s), "list": s}


def manifest(lab: str, step: str, *, target: dict, sampling: dict, seeds, inputs: dict, graders, extra=None,
             packages=PACKAGES) -> dict:
    hashed = {}
    for name, v in (inputs or {}).items():
        hashed[name] = sha256_file(v) if isinstance(v, Path) else sha256_json(v)
    return {
        "lab": lab, "step": step, "run_id": uuid.uuid4().hex[:12],
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evalkit": __version__, "python": platform.python_version(),
        "platform": f"{platform.system()} {platform.machine()}",
        "packages": _versions(packages),
        "target": dict(target), "sampling": dict(sampling), "seeds": _seeds(seeds),
        "inputs_sha256": hashed, "graders": list(graders), "extra": dict(extra or {}),
    }


def write(m: dict, path):
    Path(path).write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _flat(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flat(v, key + "."))
        else:
            out[key] = v
    return out


def diff(a: dict, b: dict, ignore=("run_id", "created")) -> list:
    fa, fb = _flat(a), _flat(b)
    keys = sorted(set(fa) | set(fb))
    return [(k, fa.get(k), fb.get(k)) for k in keys
            if k.split(".")[0] not in ignore and k not in ignore and fa.get(k) != fb.get(k)]

