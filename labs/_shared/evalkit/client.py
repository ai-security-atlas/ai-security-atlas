"""A minimal OpenAI-compatible chat client (urllib only) that measures every call.

    c = Chat("http://atlas-app:8000/v1")                 # or Chat.from_env() for the .env backend block
    r = c.complete([{"role": "user", "content": "hi"}], model="atlas-support", seed=3, temperature=0.7)
    r.text, r.usage, r.latency_ms, r.raw                 # raw = the whole JSON response (e.g. atlas-app's "atlas")

Scripts print the endpoint before the first call (c.describe()); external-api steps must do so.
"""
import json
import os
import time
import urllib.error
import urllib.request


class ChatError(Exception):
    pass


class Reply:
    __slots__ = ("text", "usage", "latency_ms", "raw", "tool_calls")

    def __init__(self, text, usage, latency_ms, raw, tool_calls=None):
        self.text, self.usage, self.latency_ms, self.raw = text, usage or {}, latency_ms, raw
        self.tool_calls = tool_calls or []


class Chat:
    def __init__(self, base_url: str, api_key: str = "", model: str = "", timeout: float = 240, headers=None):
        if not base_url:
            raise ChatError("no base URL: pick a backend block in labs/.env")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.headers = dict(headers or {})

    @classmethod
    def from_env(cls, model_var: str = "LAB_CHAT_MODEL", default_model: str = "qwen2.5:3b", **kw):
        """The model backend of the .env block (LAB_LLM_BASE_URL, LAB_LLM_API_KEY)."""
        model = os.environ.get(model_var, "").strip() or default_model
        return cls(os.environ.get("LAB_LLM_BASE_URL", "").strip(), os.environ.get("LAB_LLM_API_KEY", "").strip(),
                   model, **kw)

    def describe(self) -> str:
        return f"{self.base_url} model {self.model or '-'}"

    def _req(self, method, path, body=None):
        h = {"Content-Type": "application/json", **self.headers}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base_url + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise ChatError(f"{self.base_url}{path}: HTTP {e.code}: {e.read().decode(errors='replace')[:300]}") from e
        except (urllib.error.URLError, OSError) as e:
            raise ChatError(f"{self.base_url}{path}: unreachable ({e})") from e

    def models(self) -> list:
        return [m.get("id") for m in self._req("GET", "/models").get("data", [])]

    def complete(self, messages, *, model=None, temperature=0.7, seed=None, max_tokens=200, tools=None,
                 extra=None) -> Reply:
        """One non-streaming chat completion. extra = additional body keys (e.g. atlas-app's "user")."""
        body = {"model": model or self.model, "messages": messages, "temperature": temperature,
                "max_tokens": max_tokens, "stream": False}
        if seed is not None:
            body["seed"] = seed
        if tools:
            body["tools"] = tools
        body.update(extra or {})
        t0 = time.perf_counter()
        raw = self._req("POST", "/chat/completions", body)
        ms = (time.perf_counter() - t0) * 1000
        msg = (raw.get("choices") or [{}])[0].get("message") or {}
        return Reply(msg.get("content") or "", raw.get("usage") or {}, round(ms, 1), raw, msg.get("tool_calls"))


def ollama_root(base_url: str) -> str:
    """http://host:11434/v1 -> http://host:11434 (the native Ollama API)."""
    b = (base_url or "").rstrip("/")
    return b[:-3] if b.endswith("/v1") else b


def ollama_info(base_url: str, model: str, timeout: float = 10) -> dict:
    """Version and model digest from a native Ollama API, or {"ollama": None} if the endpoint is not Ollama."""
    root = ollama_root(base_url)
    out = {"ollama": None, "digest": None}
    try:
        with urllib.request.urlopen(root + "/api/version", timeout=timeout) as r:
            out["ollama"] = json.load(r).get("version")
        with urllib.request.urlopen(root + "/api/tags", timeout=timeout) as r:
            for m in json.load(r).get("models", []):
                if m.get("name") in (model, f"{model}:latest") or m.get("model") == model:
                    out["digest"] = (m.get("digest") or "")[:12]
                    out["size"] = m.get("size")
                    out["quantization"] = (m.get("details") or {}).get("quantization_level")
    except (urllib.error.URLError, OSError, ValueError):
        pass
    return out
