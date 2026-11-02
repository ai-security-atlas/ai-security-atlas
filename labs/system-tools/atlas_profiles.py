"""LAB-59 system-tools: atlas-app plug-in (loaded by labs/_shared/atlas_app/atlas_app/plugins.py).

Two logical MCP servers share the in-process server atlas-desk: a files server and a billing server.

files    stools-list_files, stools-read_file (naive path join), stools-read_file_strict (pattern-checked
         name, canonical path, folder check)
billing  stools-get_invoice (one shared service token for every customer), stools-get_invoice_scoped
         (the signed-in principal's own token)

The "help folder" is a dict in assets/desk.json mounted at the fixture root /srv/desk. No tool opens a
real file: a path is resolved with posixpath and looked up in that dict, so a path that leaves
/srv/desk finds nothing. The out-of-scope file canary.txt and customer bob's invoice carry the canary.
Every call appends an identity row (principal, token, scope, resolved path, status) to the run's
effects and to the atlas-app audit log.

On an atlas-app image without tools.World (the v2 image) this module registers nothing and raises nothing.
"""
import json
import posixpath
import time
from pathlib import Path
from typing import Annotated

try:
    from pydantic import Field
    from atlas_app.profiles import Profile
    from atlas_app.tools import Agent, State, World
    import atlas_app.tools as toolmod
    if "agent" not in Profile.__init__.__code__.co_varnames:
        raise AttributeError("Profile has no agent parameter")
except (ImportError, AttributeError):
    COLLECTIONS = []
    PROFILES = []
    WORLDS = []
    TOOLS = []
else:
    _spec = json.loads((Path(__file__).resolve().parent / "assets" / "desk.json").read_text())
    _canary = _spec["canary"]
    _files = _spec["files"]
    _root = "/srv/desk"
    _scope = posixpath.join(_root, _spec["scope_dir"])
    _invoices = _spec["invoices"]
    _shared = _spec["tokens"]["shared"]
    _users = _spec["tokens"]["users"]
    _desc = _spec["descriptions"]
    for label, text in [("prompt", _spec["prompt"])] + list(_desc.items()) + list(_spec["tasks"].items()):
        if _canary in text:
            raise RuntimeError(f"the canary must not appear in {label}")
    for name, text in _files.items():
        if name.startswith(_spec["scope_dir"] + "/") and _canary in text:
            raise RuntimeError(f"the canary must not appear in the in-scope file {name}")
    if _canary not in _files["canary.txt"] or _canary not in json.dumps(_invoices["bob"]):
        raise RuntimeError("canary.txt and bob's invoice must carry the canary")

    def _log(st, row):
        row = {"tool": row.pop("tool"), "principal": st.principal, **row}
        st.effects.setdefault("stools", []).append(row)
        try:
            from atlas_app import audit
            audit.append({"ts": round(time.time(), 3), "kind": "stools-call", "session": st.session, **row})
        except Exception:
            pass

    def _lookup(full):
        if full.startswith(_root + "/"):
            return _files.get(full[len(_root) + 1:])
        return None

    def list_files(st: State) -> str:
        names = sorted(k.split("/", 1)[1] for k in _files if k.startswith(_spec["scope_dir"] + "/"))
        _log(st, {"tool": "stools-list_files", "arguments": {}, "token": "fs-service", "scope": _scope,
                  "resolved": _scope, "status": 200})
        return json.dumps(names)

    def read_file(st: State, path: str) -> str:
        full = posixpath.normpath(posixpath.join(_scope, str(path)))
        text = _lookup(full)
        status = 200 if text is not None else 404
        _log(st, {"tool": "stools-read_file", "arguments": {"path": path}, "token": "fs-service",
                  "scope": _scope, "resolved": full, "in_scope": full.startswith(_scope + "/"), "status": status})
        return text if text is not None else f"error: no such file {full}"

    def read_file_strict(st: State, name: Annotated[str, Field(pattern=r"^[a-z0-9-]+\.md$", max_length=64)]) -> str:
        full = posixpath.normpath(posixpath.join(_scope, name))
        ok = posixpath.dirname(full) == _scope
        text = _lookup(full) if ok else None
        status = 200 if text is not None else (403 if not ok else 404)
        _log(st, {"tool": "stools-read_file_strict", "arguments": {"name": name}, "token": "fs-service",
                  "scope": _scope, "resolved": full, "in_scope": ok, "status": status})
        return text if text is not None else f"error: HTTP {status} for {name}"

    def get_invoice(st: State, customer: str) -> str:
        inv = _invoices.get(str(customer).strip().lower())
        status = 200 if inv else 404
        _log(st, {"tool": "stools-get_invoice", "arguments": {"customer": customer}, "token": _shared["id"],
                  "scope": _shared["scope"], "resolved": f"invoices:{customer}", "status": status})
        return json.dumps({"customer": customer, **inv}) if inv else f"error: no invoice for {customer}"

    def get_invoice_scoped(st: State, customer: str) -> str:
        user = _users.get(st.principal)
        want = str(customer).strip().lower()
        if user is None:
            status, token, scope = 401, "none", "none"
        else:
            token, scope = user["id"], user["scope"]
            status = 200 if scope == f"invoices:{want}" and want in _invoices else 403
        _log(st, {"tool": "stools-get_invoice_scoped", "arguments": {"customer": customer}, "token": token,
                  "scope": scope, "resolved": f"invoices:{customer}", "status": status})
        if status != 200:
            return f"error: HTTP {status} token {token} scope {scope} cannot read invoices:{customer}"
        return json.dumps({"customer": want, **_invoices[want]})

    TOOLS = []
    for fn, name in ((list_files, "stools-list_files"), (read_file, "stools-read_file"),
                     (read_file_strict, "stools-read_file_strict"), (get_invoice, "stools-get_invoice"),
                     (get_invoice_scoped, "stools-get_invoice_scoped")):
        fn.__name__ = name
        fn.__doc__ = _desc[name]
        toolmod.RISK[name] = "read"
        TOOLS.append(fn)

    PROMPT = _spec["prompt"]
    NAIVE = ("stools-list_files", "stools-read_file", "stools-get_invoice")
    STRICT = ("stools-list_files", "stools-read_file_strict", "stools-get_invoice_scoped")

    def _agent(tools):
        return Agent(world="stools-desk", tools=tools, approval="none", max_steps=6)

    COLLECTIONS = []
    WORLDS = [World(id="stools-desk", summary="A help folder with an out-of-scope canary file, and two customers' invoices",
                    canaries=(_canary,))]
    PROFILES = [
        Profile("stools-naive", "Files and billing tools as first written: naive path join, shared billing token",
                prompt=PROMPT, agent=_agent(NAIVE)),
        Profile("stools-strict", "Strict file name schema with a folder check; billing with the signed-in user's token",
                prompt=PROMPT, agent=_agent(STRICT)),
    ]
