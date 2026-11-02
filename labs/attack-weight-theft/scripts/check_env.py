"""Setup 3: the victim answers with no password, and the fine-tune is loaded.

    docker compose run --rm workbench python attack-weight-theft/scripts/check_env.py
"""
import labkit

import theftkit

labkit.banner()

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror})")

if labkit.backend():
    print("[note] LAB_BACKEND is set; this lab does not call it. The victim is victim-ollama on the lab network.")

try:
    status, info = theftkit.version()
    print(f"[ok] victim-ollama {info.get('version')} at {theftkit.VICTIM} HTTP {status} (no Authorization header)")
except Exception as e:
    print(f"[!!] victim-ollama: {e}")
    print("[!!] start the lab stack: see Setup 2")
    raise SystemExit(1)

try:
    status, models = theftkit.tags()
    names = [m["name"] for m in models.get("models", [])]
    digest = theftkit.digest_of(models.get("models", []), theftkit.MODEL)
    print(f"[ok] GET /api/tags HTTP {status} models: {', '.join(names)}")
    print(f"[ok] {theftkit.MODEL} digest {digest}")
except Exception as e:
    print(f"[!!] /api/tags: {e}")
    raise SystemExit(1)

try:
    status, shown = theftkit.show(theftkit.MODEL)
    text = shown.get("modelfile", "") + "\n" + shown.get("system", "")
    mark = "ok" if theftkit.CANARY in text else "!!"
    print(f"[{mark}] POST /api/show HTTP {status}; canary {theftkit.CANARY} in Modelfile: {theftkit.CANARY in text}")
except Exception as e:
    print(f"[!!] /api/show: {e}")
    raise SystemExit(1)

try:
    status, body = theftkit.get(theftkit.REGISTRY + "/v2/", timeout=15)
    print(f"[ok] registry {theftkit.REGISTRY}/v2/ HTTP {status} body {body.decode()[:40]!r}")
except theftkit.HttpStatus as e:
    print(f"[!!] registry HTTP {e.status} (Setup 2 should recreate it without a password)")
    raise SystemExit(1)
except Exception as e:
    print(f"[!!] registry: {e}")
    raise SystemExit(1)
