"""serving: the shared llama.cpp server fixture (compose profile `serving`; founded by LAB-14 system-serving).

    import serving                      # PYTHONPATH=/labs/_shared is set on the workbench and sandbox

Compose services (profile `serving`, labs/compose.yaml):

* `serving-model` (one-shot, workbench image): `python -m serving.fetch` downloads MODEL at its
  pinned revision into the shared HF cache (hf-cache-v1) and checks its sha256. llama-server waits
  for it to succeed.
* `llama-server`: IMAGE (llama.cpp build LLAMA_BUILD, multi-arch amd64/arm64, pinned by digest),
  read-only, uid 1000, no capabilities. It serves on port 8080 on the compose network
  (BASE_URL = http://llama-server:8080) and on 127.0.0.1:${SERVING_PORT:-8180} on the host.
  Its flags are the image defaults plus:
    --model ${SERVING_MODEL:-<MODEL path>}   any GGUF readable inside the container: the HF cache
                                             (/cache/hf, read-only) or the checkout (/labs, read-only),
                                             e.g. SERVING_MODEL=/labs/format-gguf/work/x.gguf
    --alias ${SERVING_ALIAS:-smollm2-360m}  the model id the API reports
    ${SERVING_ARGS}                         extra flags, e.g. SERVING_ARGS="--metrics --no-slots"
  LLAMA_ARG_THREADS=${SERVING_CPU_THREADS:-4}. A healthcheck polls /health, so
  `docker compose up -d --wait llama-server` returns once the model is loaded.
  Change flags or the model by re-running `up` with new values (compose recreates the container):
      SERVING_ARGS="--api-key-file /labs/_shared/serving/lab-api-keys.txt" docker compose up -d --wait llama-server
      docker compose up -d --wait llama-server          # back to the shipped defaults
* `llama-server-hardened`: the same image and model with the hardened reference flags HARDENED_ARGS
  (API key file, no /slots, no web UI, per-request token cap, parallel slots, short timeout, CORS
  limited to localhost). http://llama-server-hardened:8080, host port ${SERVING_HARDENED_PORT:-8181}.

Facts measured on LLAMA_BUILD (record them again if you change IMAGE; defaults move between builds):
the image sets LLAMA_ARG_HOST=0.0.0.0 and LLAMA_ARG_PORT=8080 (the binary's own defaults are
127.0.0.1:9931); /slots is on, /metrics and POST /props are off, there is no API key, n_predict is
-1 (unlimited), the HTTP timeout is 3600 s, prompt caching is on, CORS allows any origin with
credentials, and the web UI is on.

Client helpers (stdlib only, so they also run in the sandbox): get(), post(), wait_ready(),
chat(), complete(), probe() (one row of the endpoint exposure table), percentile(). Requests carry
an optional Bearer key. The budget proxy for the Defend steps is serving.proxy.

The lab's API key (LAB_KEY, in lab-api-keys.txt) is a fixed, non-secret lab value, like the
Open WebUI default secret: never reuse it outside the lab.
"""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

LLAMA_BUILD = "b11977"
IMAGE = ("ghcr.io/ggml-org/llama.cpp:server-b11977"
         "@sha256:01c2bc28d51291536df2ccebe5c6af1cdec9ea9b2bd98ac59556408caf96d3f8")

MODEL = {
    "alias": "smollm2-360m",
    "repo": "HuggingFaceTB/SmolLM2-360M-Instruct-GGUF",
    "revision": "593b5a2e04c8f3e4ee880263f93e0bd2901ad47f",
    "file": "smollm2-360m-instruct-q8_0.gguf",
    "size": 386404992,
    "sha256": "48ab3034d0dd401fbc721eb1df3217902fee7dab9078992d66431f09b7750201",
}

BASE_URL = "http://llama-server:8080"
HARDENED_URL = "http://llama-server-hardened:8080"
LAB_KEY = (HERE / "lab-api-keys.txt").read_text().split()[-1]


def model_path(hf_home="/cache/hf") -> Path:
    repo = MODEL["repo"].replace("/", "--")
    return Path(hf_home) / "hub" / f"models--{repo}" / "snapshots" / MODEL["revision"] / MODEL["file"]


class Resp:
    """A finished HTTP exchange: status, headers (lower-case keys), body text, seconds."""

    def __init__(self, status, headers, body, seconds, error=None):
        self.status, self.headers, self.body, self.seconds, self.error = status, headers, body, seconds, error

    def json(self):
        try:
            return json.loads(self.body)
        except (TypeError, ValueError):
            return None

    def __repr__(self):
        return f"Resp({self.status}, {len(self.body or '')} bytes, {self.seconds:.2f}s)"


def request(method, url, body=None, key=None, headers=None, timeout=300):
    """One HTTP request. Never raises for HTTP errors; a connection failure gives status 0 and .error."""
    h = {"Content-Type": "application/json"} if body is not None else {}
    if key:
        h["Authorization"] = f"Bearer {key}"
    h.update(headers or {})
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            text = r.read().decode("utf-8", "replace")
            return Resp(r.status, {k.lower(): v for k, v in r.headers.items()}, text, time.perf_counter() - t0)
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        return Resp(e.code, {k.lower(): v for k, v in e.headers.items()}, text, time.perf_counter() - t0)
    except (urllib.error.URLError, OSError) as e:
        reason = getattr(e, "reason", e)
        return Resp(0, {}, "", time.perf_counter() - t0, error=f"{type(reason).__name__}: {reason}")


def get(base, path, key=None, **kw):
    return request("GET", base + path, key=key, **kw)


def post(base, path, body, key=None, **kw):
    return request("POST", base + path, body=body, key=key, **kw)


def wait_ready(base, key=None, timeout=120):
    """Wait until GET /health answers 200; return the seconds waited or raise RuntimeError."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = get(base, "/health", key=key, timeout=5)
        if r.status == 200:
            return time.time() - t0
        time.sleep(0.5)
    raise RuntimeError(f"{base}/health not ready after {timeout}s (last: {r.status} {r.error or r.body[:80]})")


def chat(base, messages, key=None, timeout=300, **params):
    """POST /v1/chat/completions (temperature 0 unless given). Returns Resp."""
    body = {"model": MODEL["alias"], "messages": messages, "temperature": 0}
    body.update(params)
    return post(base, "/v1/chat/completions", body, key=key, timeout=timeout)


def complete(base, prompt, key=None, timeout=300, **params):
    """POST /completion, the native endpoint (n_predict, cache_prompt, id_slot ...). Returns Resp."""
    body = {"prompt": prompt, "temperature": 0}
    body.update(params)
    return post(base, "/completion", body, key=key, timeout=timeout)


def percentile(xs, q):
    """Nearest-rank percentile of a non-empty list (q in 0..100)."""
    s = sorted(xs)
    k = max(0, min(len(s) - 1, int(round(q / 100 * len(s) + 0.5)) - 1))
    return s[k]
