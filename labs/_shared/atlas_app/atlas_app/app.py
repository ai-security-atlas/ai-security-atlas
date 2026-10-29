"""atlas-app: the "Atlas Widgets" support assistant, a shared lab fixture (founded by LAB-06).

An OpenAI-compatible chat app: Open WebUI can use it as an OpenAI connection, and lab scripts call it
over HTTP. The operator's system prompt and policy live here, server side; a client only ever sends
messages. Every turn goes to the configured model backend (backend.py) and to the audit log (audit.py).

HTTP API (port 8000; compose service `atlas-app`, profile `rag-agent`):

  GET  /healthz                 {"ok", "version", "backend", "base_url", "chat_model", "canary", "profiles"}
  GET  /v1/models               OpenAI model list; one entry per profile (profiles.py)
  POST /v1/chat/completions     OpenAI chat completions. Body: model (a profile id), messages,
                                temperature (0.7), seed, max_tokens (200, capped at 400), stream.
                                Extra, optional: backend_model (override LAB_CHAT_MODEL for this call),
                                user or header X-Atlas-Session (audit session id).
                                Client "system"/"developer" messages are demoted to user turns: the
                                operator slot is not part of the public API.
                                The response adds a non-standard "atlas" object:
                                {request_id, profile, layers, backend_model, findings, blocked_by, canary}.
  GET  /admin/audit?n=&session= the last n audit entries (operator view; JSON list)
  POST /admin/reset             clear the audit log -> {"removed": n}
  GET  /admin/profiles          profile ids, summaries and layers (never the prompt text)

The /admin routes are the operator's side of a real deployment: here they share the port for
convenience, and the port is published on 127.0.0.1 only.
"""
import json
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from . import __version__, audit, backend, policy, world
from .profiles import PROFILES

app = FastAPI(title="atlas-app", version=__version__)
MAX_TOKENS_CAP = 400


def _err(status, message, kind="invalid_request_error", code=None):
    return JSONResponse({"error": {"message": message, "type": kind, "code": code}}, status_code=status)


def _text(content) -> str:
    """Message content as text (OpenAI allows a string or a list of parts)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    return ""


def build_context(profile, messages):
    """The messages the model receives, and their shape for the audit log."""
    ctx = [{"role": "system", "content": profile.system_prompt()}]
    shape = [{"role": "system", "source": "operator", "chars": len(ctx[0]["content"])}]
    for m in messages:
        role, text = m.get("role"), _text(m.get("content"))
        if role in ("system", "developer"):
            role, source = "user", f"client-{m.get('role')} (demoted)"
        elif role == "user":
            source = "client"
        elif role == "assistant":
            source = "client-history"
        else:
            continue
        if role == "user":
            text = profile.wrap_user(text)
        ctx.append({"role": role, "content": text})
        shape.append({"role": role, "source": source, "chars": len(text)})
    return ctx, shape


@app.get("/healthz")
def healthz():
    return {"ok": True, "version": __version__, "backend": backend.NAME, "base_url": backend.BASE_URL,
            "chat_model": backend.CHAT_MODEL, "canary": world.CANARY, "profiles": list(PROFILES)}


@app.get("/v1/models")
def models():
    now = int(time.time())
    return {"object": "list", "data": [{"id": p.id, "object": "model", "created": now, "owned_by": "atlas-app"}
                                      for p in PROFILES.values()]}


@app.get("/admin/profiles")
def admin_profiles():
    return [{"id": p.id, "summary": p.summary, "layers": p.layers()} for p in PROFILES.values()]


@app.get("/admin/audit")
def admin_audit(n: int = 50, session: str = None):
    return audit.tail(n, session)


@app.post("/admin/reset")
def admin_reset():
    return {"removed": audit.reset()}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _err(400, "body must be JSON")
    profile = PROFILES.get(body.get("model"))
    if profile is None:
        return _err(404, f"model {body.get('model')!r} not found; GET /v1/models lists the profiles",
                    code="model_not_found")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        return _err(400, "messages must be a non-empty list")

    rid = uuid.uuid4().hex[:12]
    session = request.headers.get("x-atlas-session") or body.get("user") or "-"
    ctx, shape = build_context(profile, messages)
    params = {"temperature": body.get("temperature", 0.7), "seed": body.get("seed"),
              "max_tokens": min(int(body.get("max_tokens") or 200), MAX_TOKENS_CAP)}
    t0 = time.time()
    entry = {"ts": round(t0, 3), "request_id": rid, "session": session, "profile": profile.id,
             "layers": profile.layers(), "context": shape, "params": params,
             "input": _text(messages[-1].get("content"))[:1000]}
    try:
        res = await backend.chat(ctx, model=body.get("backend_model"), **params)
    except backend.BackendError as e:
        audit.append({**entry, "error": str(e)})
        return _err(502, str(e), kind="backend_error")

    raw = res["content"]
    findings = policy.scan(raw)
    blocked = "output-policy" if profile.output_check and findings else None
    reply = world.SAFE_REPLY if blocked else raw
    atlas = {"request_id": rid, "profile": profile.id, "layers": profile.layers(), "backend_model": res["model"],
             "findings": findings, "blocked_by": blocked, "canary": policy.has_canary(reply)}
    audit.append({**entry, "backend_model": res["model"], "usage": res["usage"],
                  "latency_ms": int((time.time() - t0) * 1000), "model_reply": raw[:2000],
                  "reply": reply[:2000], "findings": findings, "blocked_by": blocked,
                  "canary": atlas["canary"]})

    cid, created = f"chatcmpl-{rid}", int(t0)
    if body.get("stream"):
        def sse():
            def chunk(delta, finish=None, **extra):
                return "data: " + json.dumps({"id": cid, "object": "chat.completion.chunk", "created": created,
                                              "model": profile.id, "choices": [{"index": 0, "delta": delta,
                                                                                "finish_reason": finish}], **extra}) + "\n\n"
            # The whole reply is checked before the first byte is sent (an output check cannot stream).
            yield chunk({"role": "assistant", "content": ""})
            yield chunk({"content": reply})
            yield chunk({}, "stop", usage=res["usage"], atlas=atlas)
            yield "data: [DONE]\n\n"
        return StreamingResponse(sse(), media_type="text/event-stream")
    return {"id": cid, "object": "chat.completion", "created": created, "model": profile.id,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}],
            "usage": res["usage"], "atlas": atlas}
