"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-indirect-injection/scripts/check_env.py
Checks the workbench, fixture-web (pages, mailbox, collector), atlas-app's RAG index and this lab's plug-in,
and the model backend behind atlas-app (container Ollama: pulls LAB_CHAT_MODEL if it is missing).
"""
import json
import os
import time
import urllib.request

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import inbox as I  # noqa: E402

print(f"[ok] evalkit {ek.__version__}")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")


def wait(fn, what):
    err = None
    for _ in range(12):
        try:
            return fn()
        except (OSError, SystemExit) as e:
            err = e
            time.sleep(2.5)
    raise SystemExit(f"[!!] {what} unreachable ({err})")


f = wait(lambda: I.web("/healthz"), f"fixture-web at {I.WEB}")
print(f"[ok] fixture-web {f['version']} at {I.WEB}: {f['mail']} emails, {f['pages']} pages, collector on /collect "
      "(compose network only)")
h = wait(lambda: I.app("/healthz"), f"atlas-app at {I.APP}")
rag = h.get("rag")
if not rag or not rag["ready"]:
    raise SystemExit(f"[!!] atlas-app RAG index not ready: {rag and rag['error']}; rebuild it "
                     "(`docker compose build atlas-app`)")
mine = (h.get("plugins") or {}).get(labkit.node_id())
if not mine:
    errs = [e["error"] for e in h.get("plugin_errors", []) if e["lab"] == labkit.node_id()]
    raise SystemExit(f"[!!] the {labkit.node_id()} plug-in is not loaded: "
                     + (errs[0] if errs else "atlas-app does not see labs/ (it needs the read-only labs/ mount and "
                                             "ATLAS_APP_LABS=/labs from labs/compose.yaml)"))
coll = mine["collections"][0]
print(f"[ok] plug-in {labkit.node_id()}: profiles {' '.join(mine['profiles'])}; "
      f"collection {coll} ({rag['collections'].get(coll)} chunks)")
if h["backend"] == "none" or not h["base_url"]:
    raise SystemExit("[!!] atlas-app has no model backend: this lab needs one (pick a backend block in labs/.env)")
print(f"[note] atlas-app model backend: {h['backend']} {h['base_url']} model {h['chat_model']}", flush=True)

if h["backend"] == "container-ollama":
    base = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
    with urllib.request.urlopen(base + "/api/tags", timeout=15) as r:
        have = {m["name"] for m in json.load(r).get("models", [])}
    if h["chat_model"] not in have and h["chat_model"] + ":latest" not in have:
        print(f"[note] pulling {h['chat_model']} into container Ollama ({base}); about 1.9 GB, once", flush=True)
        req = urllib.request.Request(base + "/api/pull", data=json.dumps({"model": h["chat_model"], "stream": False}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=3600).read()

try:
    r = I.ask("xinj-inbox", I.cases()["email-clean"]["ask"], seed=0)
    print(f"[ok] {h['chat_model']} answers through atlas-app as Riley: {I.short(r.text, 50)}")
except SystemExit as e:
    print(f"{e}\n[!!] the backend did not answer; host Ollama: run `ollama pull {h['chat_model']}` on the host")
