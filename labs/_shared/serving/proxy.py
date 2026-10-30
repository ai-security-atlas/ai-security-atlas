"""A small budget gateway in front of a llama.cpp server (stdlib only; LAB-14 system-serving D3).

    from serving.proxy import Policy, serve
    policy = Policy(upstream=serving.HARDENED_URL, upstream_key=serving.LAB_KEY,
                    tenants={"tenant-a-key": ("A", 0), "tenant-b-key": ("B", 1)})
    with serve(policy) as url:          # http://127.0.0.1:<free port>, inside the calling container
        serving.chat(url, [...], key="tenant-a-key")

What it enforces, in this order (the reply says which rule refused a request):
  1. a key per tenant (401 for an unknown key); the upstream key never leaves the gateway;
  2. a path allowlist: only POST /v1/chat/completions and GET /v1/models (404 for anything else,
     so /slots, /props, /metrics, /tokenize and the web UI are not reachable through it);
  3. per-tenant concurrency (max_concurrent, default 1; 429, no queue);
  4. a per-tenant token budget over a sliding window (tokens_per_window per window_s; 429). A request
     is refused when the tokens used in the window plus its max_tokens would pass the budget;
  5. a request-body allowlist (BODY_KEYS): every other field (n_predict, ignore_eos, id_slot,
     cache_prompt, n_probs, stream, ...) is dropped, and max_tokens is clamped to Policy.max_tokens;
  6. the tenant's own slot: id_slot is set from the tenant table, so tenants never share a slot's cache;
  7. response scrubbing: the llama.cpp `timings` object (cache_n, prompt_ms, ...) is removed
     unless strip_timings=False.
Every request is logged as one JSON line to Policy.log_path (if set): time, tenant, path, status, rule,
max_tokens served, usage.
"""

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BODY_KEYS = {"model", "messages", "temperature", "top_p", "max_tokens", "seed", "stop"}
ALLOW = {("POST", "/v1/chat/completions"), ("GET", "/v1/models")}


@dataclass
class Policy:
    upstream: str
    upstream_key: str
    tenants: dict                      # key -> (tenant name, slot id)
    max_tokens: int = 128
    max_concurrent: int = 1
    tokens_per_window: int = 1000
    window_s: float = 60.0
    strip_timings: bool = True
    pin_slots: bool = True
    upstream_timeout: float = 60.0
    log_path: object = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _inflight: dict = field(default_factory=dict, repr=False)
    _used: dict = field(default_factory=dict, repr=False)       # tenant -> [(t, tokens)]

    def used(self, tenant, now=None):
        now = now or time.time()
        keep = [(t, n) for t, n in self._used.get(tenant, []) if now - t < self.window_s]
        self._used[tenant] = keep
        return sum(n for _, n in keep)


class _Handler(BaseHTTPRequestHandler):
    policy: Policy = None
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):          # quiet
        pass

    def _send(self, status, obj, rule=None, tenant=None, extra=None):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if rule:
            self.send_header("X-Gateway-Rule", rule)
        self.end_headers()
        self.wfile.write(body)
        p = self.policy
        if p.log_path:
            line = {"t": round(time.time(), 3), "tenant": tenant, "method": self.command, "path": self.path,
                    "status": status, "rule": rule}
            line.update(extra or {})
            with p._lock, open(p.log_path, "a") as f:
                f.write(json.dumps(line) + "\n")

    def _deny(self, status, rule, msg, tenant=None):
        self._send(status, {"error": {"code": status, "message": msg, "type": "gateway_" + rule}}, rule, tenant)

    def _handle(self):
        p = self.policy
        auth = self.headers.get("Authorization", "")
        key = auth[7:] if auth.startswith("Bearer ") else ""
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        if key not in p.tenants:
            return self._deny(401, "auth", "unknown or missing tenant key")
        tenant, slot = p.tenants[key]
        path = self.path.split("?")[0]
        if (self.command, path) not in ALLOW:
            return self._deny(404, "path", f"{self.command} {path} is not exposed by the gateway", tenant)
        body = None
        max_tokens = None
        if self.command == "POST":
            try:
                req = json.loads(raw or b"{}")
            except ValueError:
                return self._deny(400, "body", "body is not JSON", tenant)
            asked = req.get("max_tokens", req.get("n_predict", p.max_tokens))
            if not isinstance(asked, int) or asked <= 0:
                asked = p.max_tokens
            max_tokens = min(asked, p.max_tokens)
            body = {k: v for k, v in req.items() if k in BODY_KEYS}
            body["max_tokens"] = max_tokens
            if p.pin_slots:
                body["id_slot"] = slot
        with p._lock:
            if p._inflight.get(tenant, 0) >= p.max_concurrent:
                busy = True
            else:
                busy = False
                if max_tokens and p.used(tenant) + max_tokens > p.tokens_per_window:
                    over = True
                else:
                    over = False
                    p._inflight[tenant] = p._inflight.get(tenant, 0) + 1
        if busy:
            return self._deny(429, "concurrency", f"tenant {tenant} already has {p.max_concurrent} request(s) running", tenant)
        if max_tokens and over:
            return self._deny(429, "budget", f"tenant {tenant} token budget {p.tokens_per_window}/{p.window_s:.0f}s used up", tenant)
        try:
            data = json.dumps(body).encode() if body is not None else None
            up = urllib.request.Request(p.upstream + path, data=data, method=self.command,
                                        headers={"Authorization": f"Bearer {p.upstream_key}",
                                                 "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(up, timeout=p.upstream_timeout) as r:
                    status, text = r.status, r.read()
            except urllib.error.HTTPError as e:
                status, text = e.code, e.read()
            except (urllib.error.URLError, OSError) as e:
                return self._deny(502, "upstream", f"upstream error: {e}", tenant)
            try:
                obj = json.loads(text)
            except ValueError:
                obj = {"error": {"message": text[:200].decode("utf-8", "replace")}}
            usage = obj.get("usage") if isinstance(obj, dict) else None
            if p.strip_timings and isinstance(obj, dict):
                obj.pop("timings", None)
            spent = (usage or {}).get("total_tokens", 0)
            with p._lock:
                p._used.setdefault(tenant, []).append((time.time(), spent))
            self._send(status, obj, None, tenant, {"max_tokens": max_tokens, "usage": usage})
        finally:
            with p._lock:
                p._inflight[tenant] = max(0, p._inflight.get(tenant, 1) - 1)

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_OPTIONS(self):               # no CORS headers: browsers on other origins are refused
        self._handle()

    def do_DELETE(self):
        self._handle()


@contextmanager
def serve(policy, host="127.0.0.1", port=0, quiet=False):
    """Run the gateway in a background thread; yield its base URL; stop it on exit."""
    if port == 0:
        with socket.socket() as s:
            s.bind((host, 0))
            port = s.getsockname()[1]
    handler = type("Handler", (_Handler,), {"policy": policy})
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.daemon_threads = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    url = f"http://{host}:{port}"
    if not quiet:
        print(f"[note] budget gateway {url} (inside this container) -> {policy.upstream}", flush=True)
    try:
        yield url
    finally:
        httpd.shutdown()
        httpd.server_close()
