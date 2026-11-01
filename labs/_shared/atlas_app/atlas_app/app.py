"""atlas-app: the "Atlas Widgets" support assistant, a shared lab fixture (founded by LAB-06).

An OpenAI-compatible chat app: Open WebUI can use it as an OpenAI connection, and lab scripts call it
over HTTP. The operator's system prompt and policy live here, server side; a client only ever sends
messages. Every turn goes to the configured model backend (backend.py) and to the audit log (audit.py).

HTTP API (port 8000; compose service `atlas-app`, profile `rag-agent`):

  GET  /healthz                 {"ok", "version", "backend", "base_url", "chat_model", "canary", "profiles",
                                 "plugins", "plugin_errors", "rag"}; "profiles" lists the core (LAB-06)
                                profiles only, "plugins" maps each lab folder to the profiles and
                                collections it registered (plugins.py)
  GET  /v1/models               OpenAI model list; one entry per profile, core and plug-in
  POST /v1/chat/completions     OpenAI chat completions. Body: model (a profile id), messages,
                                temperature (0.7), seed, max_tokens (200, capped at 400), stream.
                                Extra, optional: backend_model (override LAB_CHAT_MODEL for this call),
                                user or header X-Atlas-Session (audit session id).
                                Client "system"/"developer" messages are demoted to user turns: the
                                operator slot is not part of the public API.
                                The response adds a non-standard "atlas" object:
                                {request_id, profile, layers, backend_model, findings, blocked_by, canary},
                                plus "rag" for RAG profiles (below).
  GET  /admin/audit?n=&session= the last n audit entries (operator view; JSON list)
  POST /admin/reset             clear the audit log -> {"removed": n}
  GET  /admin/profiles          profile ids, summaries, layers and lab (never the prompt text)

RAG (LAB-11; rag.py, corpus.py). The caller is a principal, derived from the API key
(Authorization: Bearer atlas-key-...; corpus.PRINCIPALS); no or unknown key = anonymous. For a profile
with rag=..., the last user message is the retrieval query and the retrieved chunks are assembled into
that user turn. The response's atlas.rag is {principal, tenant, collection, k, acl, tags, retrieved:
[{id, doc_id, tenant, distance, authorized}], cited, unauthorized_cited, model_canaries (in the
model's reply), canaries (in the reply sent)}; cite_check replaces a reply that cites a document the
caller may not read (blocked_by "cite-check"). The audit entry
gets the same "rag" object. Operator stage views (no model call):
  GET  /admin/rag               embedder, collections (docs, chunks, lab, canaries), principals and keys
  GET  /admin/rag/docs?collection=   documents with metadata, text and their indexed chunks
  POST /admin/rag/chunk         {text | doc_id+collection, size, overlap} -> chunks with character spans
  POST /admin/rag/embed         {texts} -> {model, dims, vectors}
  POST /admin/rag/search        {collection, query, principal, k, acl: none|pre|post} -> ranked hits
                                (and the chromadb where-filter used for acl=pre)
  POST /admin/rag/preview       {profile, messages, principal} -> the exact messages the model would get

The /admin routes are the operator's side of a real deployment: here they share the port for
convenience, and the port is published on 127.0.0.1 only.

Agent profiles (LAB-22; agent.py). A profile with agent= set is not a plain chat: the client calls
POST /v1/agent/runs {profile, task|messages, world?, temperature, seed, max_tokens, session}. The app
lists the granted tools over MCP, runs an OpenAI-style tool loop against the model backend, and executes
each call with MCP tools/call on that run's private copy of the world. A gated tool pauses the run
(status "needs_approval", pending: tool, arguments, def_sha256). Resume with
POST /v1/agent/runs/{id}/decision {allow, tool, arguments?, def_sha256?, pending_id?}.
GET /admin/agent?profile= is tools/list (schemas, risk, definition sha256). POST /admin/agent/call runs
one tool on a fresh state with one decision and no model call. GET /healthz "agent" lists worlds, the
tool catalog and the agent profile ids. Chat completions are unchanged for profiles with agent=None.

Durable memory (opt-in, tools.World.persist_memory). save_memory appends a row keyed by world id and
principal, and read_memory loads those rows on the next run. The principal is the request body's
"principal" when that string is set, otherwise the API-key principal (anonymous when there is no key).
Worlds that do not set persist_memory never open the file. Operator routes, same port as the audit log:
  GET  /admin/memory?world=&principal=   every row, including expired ones
  POST /admin/memory/reset   {world?, principal?, source?} -> {"removed": n}; no filter clears the file
  POST /admin/memory/expire  {world, principal, expires, source?} -> {"updated": n}
  POST /admin/memory/row     {world, principal, note, source?, url?, session?, expires?} inserts one row
                             the operator wrote; a model save still goes through save_memory
"""
import json
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from . import (__version__, agent, audit, backend, corpus, memory_store, plugins, policy, rag,
               tools as toolmod, world)
from .profiles import ALL, PROFILES

app = FastAPI(title="atlas-app", version=__version__)
MAX_TOKENS_CAP = 400
UNAUTHORIZED_REPLY = ("I can't share that: the answer relied on a document your account is not allowed to see. "
                      "Ask about your own agreement or our public product information.")

plugins.load()
try:
    rag.build()
except Exception as e:  # RAG broken must not break the core (LAB-06) profiles
    rag.STATUS["error"] = f"{type(e).__name__}: {e}"
    print(f"[atlas-app] RAG index not built: {rag.STATUS['error']}", flush=True)


def _err(status, message, kind="invalid_request_error", code=None):
    return JSONResponse({"error": {"message": message, "type": kind, "code": code}}, status_code=status)


def _text(content) -> str:
    """Message content as text (OpenAI allows a string or a list of parts)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    return ""


def build_context(profile, messages, principal=None):
    """The messages the model receives, and their shape for the audit log."""
    ctx = [{"role": "system", "content": profile.system_prompt(principal)}]
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


def principal_of(request: Request):
    auth = request.headers.get("authorization") or ""
    return corpus.principal_for_key(auth[7:] if auth.lower().startswith("bearer ") else "")


def rag_context(profile, ctx, shape, principal, messages):
    """Retrieve for the last user turn and assemble it in place. Returns the atlas.rag object."""
    r = profile.rag
    last = max(i for i, m in enumerate(ctx) if m["role"] == "user")
    question = [_text(m.get("content")) for m in messages if m.get("role") == "user"][-1:] or [""]
    question = question[0]
    hits = rag.retrieve(r.collection, question, principal, r.k, "pre" if r.acl else "none")
    turn = rag.assemble(r, principal, question, hits)
    ctx[last]["content"] = profile.wrap_user(turn)
    shape[last] = {**shape[last], "source": shape[last]["source"] + f" + {len(hits)} retrieved chunks",
                   "chars": len(ctx[last]["content"])}
    return {"principal": principal.id, "tenant": principal.tenant, "collection": r.collection, "k": r.k,
            "acl": r.acl, "tags": r.tags,
            "retrieved": [{k: h[k] for k in ("id", "doc_id", "tenant", "distance", "authorized")} for h in hits]}


def rag_check(profile, info, reply, principal):
    """After generation: citations, canaries and (cite_check) the unauthorized-citation block."""
    coll = rag.COLLECTIONS[profile.rag.collection]
    cited = rag.citations(reply)
    bad = []
    for cid in cited:
        d = rag.resolve(coll.id, cid)
        if d is not None and not corpus.readable(principal, d.shared, d.tenant, d.roles):
            bad.append(d.id)
    bad = list(dict.fromkeys(bad))
    info.update({"cited": cited, "unauthorized_cited": bad,
                 "model_canaries": [c for c in coll.canaries if c in (reply or "")]})
    return bool(bad) and profile.rag.cite_check


@app.get("/healthz")
def healthz():
    return {"ok": True, "version": __version__, "backend": backend.NAME, "base_url": backend.BASE_URL,
            "chat_model": backend.CHAT_MODEL, "canary": world.CANARY, "profiles": list(PROFILES),
            "plugins": plugins.LOADED, "plugin_errors": plugins.ERRORS,
            "rag": {"ready": rag.STATUS["ready"], "error": rag.STATUS["error"], "embedder": rag.EMBED_MODEL,
                    "collections": {c: len(ch) for c, ch in rag.CHUNKS.items()}},
            "agent": {"worlds": [w.id for w in toolmod.WORLDS.values()], "tools": sorted(toolmod.TOOLS),
                      "profiles": [p.id for p in ALL.values() if p.agent is not None]}}


@app.get("/v1/models")
def models():
    now = int(time.time())
    return {"object": "list", "data": [{"id": p.id, "object": "model", "created": now, "owned_by": "atlas-app"}
                                      for p in ALL.values()]}


@app.get("/admin/profiles")
def admin_profiles():
    return [{"id": p.id, "summary": p.summary, "layers": p.layers(), "lab": p.lab} for p in ALL.values()]


def _rag_ready():
    if not rag.STATUS["ready"]:
        return _err(503, f"RAG index not ready: {rag.STATUS['error']}", kind="rag_error")
    return None


@app.get("/admin/rag")
def admin_rag():
    return {"ready": rag.STATUS["ready"], "error": rag.STATUS["error"], "embedder": rag.EMBED_MODEL,
            "chunk_size": rag.CHUNK_SIZE, "chunk_overlap": rag.CHUNK_OVERLAP,
            "collections": [{"id": c.id, "summary": c.summary, "lab": c.lab, "extends": c.extends,
                             "docs": len(c.docs), "chunks": len(rag.CHUNKS.get(c.id, {})),
                             "canaries": list(c.canaries)} for c in rag.COLLECTIONS.values()],
            "principals": [{"id": p.id, "tenant": p.tenant, "company": p.company, "roles": list(p.roles),
                            "key": p.key} for p in corpus.PRINCIPALS.values()]}


@app.get("/admin/rag/docs")
def admin_rag_docs(collection: str = "atlas-kb"):
    if collection not in rag.COLLECTIONS:
        return _err(404, f"collection {collection!r} not found")
    chunks = rag.CHUNKS.get(collection, {})
    return [{"id": d.id, "title": d.title, "tenant": d.tenant, "shared": d.shared, "roles": list(d.roles),
             "source": d.source, "text": d.text,
             "chunks": [{"id": c, "text": ch["text"]} for c, ch in chunks.items() if c.split("#")[0] == d.id]}
            for d in rag.COLLECTIONS[collection].docs]


@app.post("/admin/rag/chunk")
async def admin_rag_chunk(request: Request):
    body = await request.json()
    text = body.get("text")
    if text is None:
        d = rag.doc(body.get("collection") or "atlas-kb", body.get("doc_id"))
        if d is None:
            return _err(404, f"document {body.get('doc_id')!r} not found")
        text = d.text
    size, overlap = int(body.get("size") or rag.CHUNK_SIZE), int(body.get("overlap", rag.CHUNK_OVERLAP))
    return {"size": size, "overlap": overlap, "chars": len(text), "chunks": rag.chunk(text, size, overlap)}


@app.post("/admin/rag/embed")
async def admin_rag_embed(request: Request):
    body = await request.json()
    try:
        vecs = rag.embed(body.get("texts") or [])
    except Exception as e:
        return _err(503, f"embedder unavailable: {type(e).__name__}: {e}", kind="rag_error")
    return {"model": rag.EMBED_MODEL, "dims": len(vecs[0]) if vecs else 0, "vectors": vecs}


@app.post("/admin/rag/search")
async def admin_rag_search(request: Request):
    if (e := _rag_ready()) is not None:
        return e
    body = await request.json()
    coll = body.get("collection") or "atlas-kb"
    p = corpus.PRINCIPALS.get(body.get("principal") or "anonymous")
    mode = body.get("acl") or "none"
    if coll not in rag.COLLECTIONS or p is None or mode not in ("none", "pre", "post"):
        return _err(400, "need a known collection, a principal id from GET /admin/rag and acl none|pre|post")
    hits = rag.retrieve(coll, body.get("query") or "", p, int(body.get("k") or 4), mode)
    return {"collection": coll, "principal": p.id, "acl": mode,
            "where": rag.acl_filter(p) if mode == "pre" else None, "hits": hits}


@app.post("/admin/rag/preview")
async def admin_rag_preview(request: Request):
    body = await request.json()
    profile = ALL.get(body.get("profile"))
    p = corpus.PRINCIPALS.get(body.get("principal") or "anonymous")
    if profile is None or p is None or not body.get("messages"):
        return _err(400, "need a profile id, a principal id and messages")
    ctx, shape = build_context(profile, body["messages"], p)
    info = None
    if profile.rag is not None:
        if (e := _rag_ready()) is not None:
            return e
        info = rag_context(profile, ctx, shape, p, body["messages"])
    return {"profile": profile.id, "principal": p.id, "messages": ctx, "context": shape, "rag": info}


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
    profile = ALL.get(body.get("model"))
    if profile is None:
        return _err(404, f"model {body.get('model')!r} not found; GET /v1/models lists the profiles",
                    code="model_not_found")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        return _err(400, "messages must be a non-empty list")

    rid = uuid.uuid4().hex[:12]
    session = request.headers.get("x-atlas-session") or body.get("user") or "-"
    principal = principal_of(request) if profile.rag is not None else None
    ctx, shape = build_context(profile, messages, principal)
    rinfo = None
    if profile.rag is not None:
        if (e := _rag_ready()) is not None:
            return e
        rinfo = rag_context(profile, ctx, shape, principal, messages)
    params = {"temperature": body.get("temperature", 0.7), "seed": body.get("seed"),
              "max_tokens": min(int(body.get("max_tokens") or 200), MAX_TOKENS_CAP)}
    t0 = time.time()
    entry = {"ts": round(t0, 3), "request_id": rid, "session": session, "profile": profile.id,
             "layers": profile.layers(), "context": shape, "params": params,
             "input": _text(messages[-1].get("content"))[:1000]}
    if rinfo is not None:
        entry["rag"] = rinfo
    try:
        res = await backend.chat(ctx, model=body.get("backend_model"), **params)
    except backend.BackendError as e:
        audit.append({**entry, "error": str(e)})
        return _err(502, str(e), kind="backend_error")

    raw = res["content"]
    findings = policy.scan(raw)
    blocked = "output-policy" if profile.output_check and findings else None
    reply = world.SAFE_REPLY if blocked else raw
    if rinfo is not None and rag_check(profile, rinfo, raw, principal) and not blocked:
        blocked, reply = "cite-check", UNAUTHORIZED_REPLY
    atlas = {"request_id": rid, "profile": profile.id, "layers": profile.layers(), "backend_model": res["model"],
             "findings": findings, "blocked_by": blocked, "canary": policy.has_canary(reply)}
    if rinfo is not None:
        rinfo["canaries"] = [c for c in rag.COLLECTIONS[profile.rag.collection].canaries if c in reply]
        atlas["rag"] = rinfo
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


def _agent_session(request: Request, body) -> str:
    return request.headers.get("x-atlas-session") or body.get("session") or body.get("user") or "-"


def _memory_principal(request: Request, body) -> str:
    named = body.get("principal")
    if isinstance(named, str) and named.strip():
        return named.strip()
    return principal_of(request).id


@app.post("/v1/agent/runs")
async def agent_runs(request: Request):
    """Start an agent run. Returns when the model stops or a gated tool needs a decision."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _err(400, "body must be JSON")
    if body.get("max_tokens") is not None:
        body["max_tokens"] = min(int(body["max_tokens"]), MAX_TOKENS_CAP)
    else:
        body["max_tokens"] = MAX_TOKENS_CAP
    try:
        return await agent.start_run(body, _agent_session(request, body), _memory_principal(request, body))
    except agent.AgentError as e:
        return _err(e.status, str(e))
    except backend.BackendError as e:
        return _err(502, str(e), kind="backend_error")


@app.get("/v1/agent/runs/{run_id}")
def agent_run_get(run_id: str):
    try:
        return agent.get_run(run_id)
    except agent.AgentError as e:
        return _err(e.status, str(e))


@app.post("/v1/agent/runs/{run_id}/decision")
async def agent_run_decision(run_id: str, request: Request):
    """Resume a run that paused for approval. Body: allow, tool, and for args-mode the arguments and def_sha256."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _err(400, "body must be JSON")
    try:
        return await agent.decide(run_id, body)
    except agent.AgentError as e:
        return _err(e.status, str(e))
    except backend.BackendError as e:
        return _err(502, str(e), kind="backend_error")


@app.get("/admin/agent")
async def admin_agent(profile: str = None):
    """Worlds, agent profiles, and the MCP tools/list definitions (schemas and definition hashes)."""
    try:
        return await agent.catalog(profile)
    except agent.AgentError as e:
        return _err(e.status, str(e))


@app.post("/admin/agent/call")
async def admin_agent_call(request: Request):
    """One MCP tools/call on a fresh state, with one approval decision. No model call."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _err(400, "body must be JSON")
    try:
        return await agent.call_once(body, _memory_principal(request, body))
    except agent.AgentError as e:
        return _err(e.status, str(e))


@app.post("/admin/agent/reset")
def admin_agent_reset():
    return {"removed": agent.reset_runs()}


async def _json_body(request: Request) -> dict:
    raw = await request.body()
    if not raw.strip():
        return {}
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return body if isinstance(body, dict) else None


@app.get("/admin/memory")
def admin_memory(world: str = "", principal: str = ""):
    """Durable memory rows, including expired ones. Filters are optional."""
    return {"rows": memory_store.rows(world or None, principal or None, include_expired=True)}


@app.post("/admin/memory/reset")
async def admin_memory_reset(request: Request):
    """Delete durable memory rows. No filter clears the store."""
    body = await _json_body(request)
    if body is None:
        return _err(400, "body must be a JSON object")
    return {"removed": memory_store.reset(body.get("world") or None, body.get("principal") or None,
                                          body.get("source") or None)}


@app.post("/admin/memory/expire")
async def admin_memory_expire(request: Request):
    """Set expires (an ISO date) on rows for one world and principal."""
    body = await _json_body(request)
    if body is None:
        return _err(400, "body must be a JSON object")
    if not body.get("world") or not body.get("principal") or not body.get("expires"):
        return _err(400, "world, principal and expires are required")
    return {"updated": memory_store.expire(body["world"], body["principal"], str(body["expires"]),
                                           body.get("source") or None)}


@app.post("/admin/memory/row")
async def admin_memory_row(request: Request):
    """Insert one operator row. Model saves go through save_memory, not this route."""
    body = await _json_body(request)
    if body is None:
        return _err(400, "body must be a JSON object")
    if not body.get("world") or not body.get("principal") or not isinstance(body.get("note"), str):
        return _err(400, "world, principal and note are required")
    return memory_store.append(body["world"], body["principal"], body["note"],
                               str(body.get("source") or "user"), str(body.get("url") or ""),
                               str(body.get("session") or ""), str(body.get("expires") or ""))
