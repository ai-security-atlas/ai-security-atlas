"""The model backend: any OpenAI-compatible /v1 endpoint (container Ollama, host Ollama or an external API).

Configured only from the environment, i.e. from the .env backend block:
  LAB_LLM_BASE_URL  e.g. http://host.docker.internal:11434/v1
  LAB_LLM_API_KEY   sent as a Bearer token (Ollama ignores it)
  LAB_CHAT_MODEL    backend model id for the assistant (default qwen2.5:3b)
  LAB_BACKEND       backend name, for display only
"""
import json
import os

import httpx

BASE_URL = os.environ.get("LAB_LLM_BASE_URL", "").strip().rstrip("/")
API_KEY = os.environ.get("LAB_LLM_API_KEY", "").strip()
CHAT_MODEL = os.environ.get("LAB_CHAT_MODEL", "").strip() or "qwen2.5:3b"
NAME = os.environ.get("LAB_BACKEND", "").strip() or "none"
TIMEOUT = float(os.environ.get("ATLAS_APP_TIMEOUT", "180"))

_client = None


class BackendError(Exception):
    pass


def client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
        _client = httpx.AsyncClient(timeout=TIMEOUT, headers=headers)
    return _client


async def chat(messages, model=None, **params) -> dict:
    """One non-streaming chat completion. Returns {"content", "model", "usage"}."""
    if not BASE_URL:
        raise BackendError("no model backend: LAB_LLM_BASE_URL is empty (pick a backend block in labs/.env)")
    body = {"model": model or CHAT_MODEL, "messages": messages, "stream": False}
    body.update({k: v for k, v in params.items() if v is not None})
    try:
        r = await client().post(f"{BASE_URL}/chat/completions", json=body)
    except httpx.HTTPError as e:
        raise BackendError(f"backend {BASE_URL} unreachable: {type(e).__name__} {e}") from e
    if r.status_code != 200:
        raise BackendError(f"backend {BASE_URL} returned HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    msg = (data.get("choices") or [{}])[0].get("message") or {}
    return {"content": msg.get("content") or "", "model": data.get("model", body["model"]),
            "usage": data.get("usage") or {}}


def _tool_arguments(raw):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"_unparsed": raw}
        return parsed if isinstance(parsed, dict) else {"_unparsed": raw}
    if raw is None:
        return {}
    return {"_unparsed": raw}


async def chat_tools(messages, tools, model=None, **params) -> dict:
    """One non-streaming chat completion with OpenAI-style tools.

    Returns {"content", "tool_calls", "message", "model", "usage"}. tool_calls is a list of
    {"id", "name", "arguments"} with arguments already parsed into a dict. The assistant message
    is ready to append back to the conversation.
    """
    if not BASE_URL:
        raise BackendError("no model backend: LAB_LLM_BASE_URL is empty (pick a backend block in labs/.env)")
    body = {"model": model or CHAT_MODEL, "messages": messages, "tools": tools, "tool_choice": "auto",
            "stream": False}
    body.update({k: v for k, v in params.items() if v is not None})
    try:
        r = await client().post(f"{BASE_URL}/chat/completions", json=body)
    except httpx.HTTPError as e:
        raise BackendError(f"backend {BASE_URL} unreachable: {type(e).__name__} {e}") from e
    if r.status_code != 200:
        raise BackendError(f"backend {BASE_URL} returned HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    msg = (data.get("choices") or [{}])[0].get("message") or {}
    calls = []
    for i, tc in enumerate(msg.get("tool_calls") or []):
        if not isinstance(tc, dict):
            continue
        fn = tc.get("function") or {}
        name = fn.get("name") or ""
        arguments = _tool_arguments(fn.get("arguments"))
        calls.append({"id": tc.get("id") or f"call_{i}", "name": name, "arguments": arguments})
    assistant = {"role": "assistant", "content": msg.get("content") or ""}
    if calls:
        assistant["tool_calls"] = [{"id": c["id"], "type": "function",
                                    "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}}
                                   for c in calls]
    return {"content": msg.get("content") or "", "tool_calls": calls, "message": assistant,
            "model": data.get("model", body["model"]), "usage": data.get("usage") or {}}
