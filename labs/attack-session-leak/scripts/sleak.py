"""The shared multi-tenant assistant for LAB-42, as seen by the step scripts.

atlas-app already has tenants, API keys and retrieval with an optional where-filter. It does not
have a response cache or a conversation store. Those two live here, in the process, so each script
starts from an empty app. Retrieval is a real call to atlas-app's /admin/rag/search. The reply text
is a deterministic stub that quotes the top hit and any earlier turns of the same session. A live
model cross-check is separate (live()).

The caller is a principal id. The product derives that id from the Bearer key; these operator
routes take the same ids. A script never accepts a tenant name from a fictional client body.
"""
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass

import labkit

URL = os.environ.get("ATLAS_APP_URL", "http://atlas-app:8000").rstrip("/")
SPEC = json.loads(labkit.inp("assets/corpus.json").read_text())
CANARY = SPEC["canary"]
HARBOR_CODE = SPEC["harbor_code"]
SESSION_GUESS = SPEC["session_guess"]
GLOBAL_SESSION = SPEC["global_session"]
QUESTIONS = SPEC["questions"]
COLLECTION = "sleak-kb"
COPPER = "copperleaf-buyer"
HARBOR = "harbor-buyer"
KEYS = {HARBOR: "atlas-key-harbor", COPPER: "atlas-key-copperleaf"}
QIDS = ("night", "weekend", "lamp")
GUESSES = 1000


def _req(method, path, body=None, key=None, timeout=180):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(URL + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"[!!] atlas-app HTTP {e.code} on {path}: {e.read().decode()[:300]}")


def get(path):
    return _req("GET", path)


def post(path, body=None, key=None, timeout=180):
    return _req("POST", path, body or {}, key=key, timeout=timeout)


def yn(flag):
    return "yes" if flag else "no"


@dataclass
class Turn:
    principal: str
    qid: str
    cache: str
    acl: str
    memory: str
    session: str
    source: str
    reply: str
    top: str
    tenant: str
    authorized: str
    canary: bool
    leak: bool
    marker: bool
    ms: float
    unauth: int
    retrievals: int


def show(t: Turn) -> None:
    print(f"caller={t.principal} q={t.qid} cache={t.cache} acl={t.acl} memory={t.memory} "
          f"session={t.session or '-'}")
    print(f"  source={t.source} top={t.top or '-'} tenant={t.tenant or '-'} authorized={t.authorized} "
          f"canary={yn(t.canary)} leak={yn(t.leak)} marker={yn(t.marker)} ms={t.ms:.2f}")


class App:
    """One fresh assistant: an empty response cache and an empty session table."""

    def __init__(self):
        self.cache = {}
        self.sessions = {}

    def issue(self, principal):
        sid = uuid.uuid4().hex
        self.sessions[sid] = {"owner": principal, "turns": []}
        return sid

    def _search(self, principal, question, acl):
        body = {"collection": COLLECTION, "query": question, "principal": principal, "k": 4, "acl": acl}
        hits = post("/admin/rag/search", body)["hits"]
        return hits

    def ask(self, principal, qid, *, cache="off", acl="pre", memory="off", session=""):
        question = QUESTIONS[qid]
        t0 = time.perf_counter()
        norm = " ".join(question.lower().split())
        if cache == "prompt":
            ckey = ("q", norm)
        elif cache == "principal":
            ckey = ("p", principal, norm)
        else:
            ckey = None

        if ckey is not None and ckey in self.cache:
            rec = self.cache[ckey]
            reply = rec["reply"]
            ms = (time.perf_counter() - t0) * 1000
            return Turn(principal, qid, cache, acl, memory, session, "cache-hit", reply,
                        rec["top"], rec["tenant"], "cached", CANARY in reply,
                        CANARY in reply and principal != COPPER, HARBOR_CODE in reply,
                        ms, 0, 0)

        bucket, rejected = None, False
        if memory == "global":
            bucket = self.sessions.setdefault(GLOBAL_SESSION, {"owner": "", "turns": []})
        elif memory == "session":
            bucket = self.sessions.setdefault(session or GLOBAL_SESSION, {"owner": "", "turns": []})
        elif memory == "bound":
            bucket = self.sessions.get(session)
            if bucket is None or bucket["owner"] != principal:
                rejected, bucket = True, None

        if rejected:
            reply = "No session for this caller."
            ms = (time.perf_counter() - t0) * 1000
            return Turn(principal, qid, cache, acl, memory, session, "rejected", reply,
                        "", "", "-", False, False, False, ms, 0, 0)

        hits = self._search(principal, question, acl)
        prior = list(bucket["turns"]) if bucket is not None else []
        parts = []
        if prior:
            parts.append("Earlier in this session: " + " | ".join(prior))
        top = hits[0] if hits else None
        if top is None:
            parts.append("No matching document.")
        else:
            parts.append(f"Retrieved {top['doc_id']} ({top['tenant']}): {top['text']}")
        reply = " ".join(parts)
        if ckey is not None:
            self.cache[ckey] = {"reply": reply, "owner": principal,
                                "top": top["doc_id"] if top else "", "tenant": top["tenant"] if top else ""}
        if bucket is not None:
            bucket["turns"].append(reply)
        unauth = sum(not h["authorized"] for h in hits)
        ms = (time.perf_counter() - t0) * 1000
        return Turn(principal, qid, cache, acl, memory, session, "miss", reply,
                    top["doc_id"] if top else "", top["tenant"] if top else "",
                    yn(top["authorized"]) if top else "-",
                    CANARY in reply, CANARY in reply and principal != COPPER, HARBOR_CODE in reply,
                    ms, unauth, 1)


def baseline():
    """Every control on: each shop sees its own code, and Harbor does not see the canary."""
    app = App()
    copper = app.issue(COPPER)
    harbor = app.issue(HARBOR)
    rows = [
        app.ask(COPPER, "night", cache="principal", acl="pre", memory="bound", session=copper),
        app.ask(HARBOR, "night", cache="principal", acl="pre", memory="bound", session=harbor),
        app.ask(HARBOR, "weekend", cache="principal", acl="pre", memory="bound", session=harbor),
    ]
    return rows


def cache_pair():
    """Harbor asks the same question Copperleaf just asked. The cache key is the question only."""
    app = App()
    rows = [app.ask(p, "night", cache="prompt", acl="pre", memory="off") for p in (COPPER, HARBOR)]
    return rows


def workload(cache):
    """2 shops x 3 questions x 2 repeats. acl stays on, so a leak is the cache, not retrieval."""
    app = App()
    rows = []
    for _ in (1, 2):
        for principal in (COPPER, HARBOR):
            for qid in QIDS:
                rows.append(app.ask(principal, qid, cache=cache, acl="pre", memory="off"))
    hits = sum(r.source == "cache-hit" for r in rows)
    retrievals = sum(r.retrievals for r in rows)
    night = [r for r in rows if r.principal == HARBOR and r.qid == "night"]
    leaks = sum(r.leak for r in night)
    own = [r for r in rows if r.principal == COPPER and r.qid == "night"]
    return {"rows": rows, "hits": hits, "n": len(rows), "retrievals": retrievals,
            "harbor_night": len(night), "leaks": leaks, "own_canary": sum(r.canary for r in own),
            "own_n": len(own)}


def retrieval_bug():
    app = App()
    return app.ask(HARBOR, "night", cache="off", acl="none", memory="off")


def retrieval_fixed():
    app = App()
    night = app.ask(HARBOR, "night", cache="off", acl="pre", memory="off")
    weekend = app.ask(HARBOR, "weekend", cache="off", acl="pre", memory="off")
    return night, weekend


def session_bugs():
    """A shared global bucket, then a client-chosen id both shops type."""
    shared = App()
    first = shared.ask(COPPER, "night", cache="off", acl="pre", memory="global")
    second = shared.ask(HARBOR, "earlier", cache="off", acl="pre", memory="global")
    guessed = App()
    a = guessed.ask(COPPER, "night", cache="off", acl="pre", memory="session", session=SESSION_GUESS)
    b = guessed.ask(HARBOR, "earlier", cache="off", acl="pre", memory="session", session=SESSION_GUESS)
    return first, second, a, b


def session_bound():
    """The server issues the id and refuses any other id, including 1000 sequential guesses."""
    app = App()
    issued = app.issue(COPPER)
    own = app.ask(COPPER, "night", cache="off", acl="pre", memory="bound", session=issued)
    stolen = app.ask(HARBOR, "earlier", cache="off", acl="pre", memory="bound", session=issued)
    typed = app.ask(HARBOR, "earlier", cache="off", acl="pre", memory="bound", session=SESSION_GUESS)
    opened = 0
    for i in range(GUESSES):
        sid = f"sess-{i}"
        rec = app.sessions.get(sid)
        if rec is not None and rec["owner"] == HARBOR:
            opened += 1
    again = app.ask(COPPER, "earlier", cache="off", acl="pre", memory="bound", session=issued)
    return {"issued": issued, "own": own, "stolen": stolen, "typed": typed,
            "opened": opened, "guesses": GUESSES, "again": again}


def counts():
    """The deterministic numbers evaluate.py compares. No model call."""
    base = baseline()
    pair = cache_pair()
    shared = workload("prompt")
    isolated = workload("principal")
    open_hit = retrieval_bug()
    closed, utility = retrieval_fixed()
    _c1, global_h, _c2, guess_h = session_bugs()
    bound = session_bound()
    return {
        "baseline_own": int(base[0].canary),
        "baseline_cross": int(base[1].leak),
        "baseline_marker": int(base[2].marker),
        "cache_leak": int(pair[1].leak),
        "cache_source_hit": int(pair[1].source == "cache-hit"),
        "cache_hits_shared": shared["hits"],
        "cache_retrievals_shared": shared["retrievals"],
        "cache_leaks_shared": shared["leaks"],
        "cache_harbor_night": shared["harbor_night"],
        "cache_hits_isolated": isolated["hits"],
        "cache_retrievals_isolated": isolated["retrievals"],
        "cache_leaks_isolated": isolated["leaks"],
        "cache_own_isolated": isolated["own_canary"],
        "cache_own_n": isolated["own_n"],
        "retrieval_leak": int(open_hit.leak),
        "retrieval_unauth": open_hit.unauth,
        "retrieval_top": open_hit.top,
        "acl_leak": int(closed.leak),
        "acl_unauth": closed.unauth,
        "acl_utility": int(utility.marker),
        "session_global_leak": int(global_h.leak),
        "session_guess_leak": int(guess_h.leak),
        "bound_stolen": int(bound["stolen"].leak),
        "bound_typed": int(bound["typed"].source == "rejected"),
        "bound_own": int(bound["again"].canary),
        "guesses_opened": bound["opened"],
        "guesses": bound["guesses"],
        "workload_n": shared["n"],
    }


def note_backend():
    h = get("/healthz")
    print(f"[note] -> {URL} (backend {h.get('backend')}: {h.get('base_url')} model {h.get('chat_model')})",
          flush=True)
    return h


def live(trials=4):
    """Seeded quotes from qwen (or whatever atlas-app is pointed at). Best-effort.

    Returns a dict, or None when the backend is missing or a call fails. The stub counts
    do not depend on this.
    """
    h = get("/healthz")
    if h.get("backend") in (None, "", "none") or not h.get("base_url"):
        print("[skip] live cross-check: atlas-app has no model backend")
        return None
    question = QUESTIONS["night"]
    out = {"model": h.get("chat_model"), "backend": h.get("backend"), "trials": trials, "profiles": {}}
    try:
        for profile in ("sleak-open", "sleak-acl"):
            rows = []
            for seed in range(trials):
                t0 = time.perf_counter()
                body = {"model": profile, "messages": [{"role": "user", "content": question}],
                        "temperature": 0, "seed": seed, "max_tokens": 60, "user": f"lab42-s{seed}"}
                res = post("/v1/chat/completions", body, key=KEYS[HARBOR])
                ms = (time.perf_counter() - t0) * 1000
                reply = res["choices"][0]["message"]["content"]
                usage = res.get("usage") or {}
                rows.append({"seed": seed, "leak": CANARY in reply, "ms": round(ms, 1),
                             "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                             "completion_tokens": int(usage.get("completion_tokens") or 0),
                             "reply": reply})
            leaks = sum(r["leak"] for r in rows)
            out["profiles"][profile] = {"leaks": leaks, "n": trials, "rows": rows}
            print(f"live {profile} leak {leaks}/{trials}", flush=True)
    except (OSError, SystemExit, KeyError, urllib.error.URLError) as e:
        print(f"[skip] live cross-check: {e}")
        return None
    return out
