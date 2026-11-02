"""Step 1: list models and read the fine-tune Modelfile. No password is sent.

    docker compose run --rm workbench python attack-weight-theft/scripts/s01_surface.py
"""
import json

import labkit

import theftkit

labkit.banner()

status, models = theftkit.tags()
rows = models.get("models", [])
print(f"[ok] GET /api/tags HTTP {status} without Authorization")
print(f"{'name':<40} {'digest':<64} {'size':>12}")
for m in rows:
    print(f"{m['name']:<40} {m['digest']:<64} {m['size']:>12}")

ft = theftkit.digest_of(rows, theftkit.MODEL)
base = theftkit.digest_of(rows, theftkit.BASE)
print(f"[ok] fine-tune digest differs from public base: {bool(ft and base and ft != base)}")

show_status, shown = theftkit.show(theftkit.MODEL)
system = shown.get("system", "").replace("\n", " ")
print(f"[ok] POST /api/show HTTP {show_status}")
print(f"SYSTEM {system}")
license_lines = [ln.strip() for ln in shown.get("license", "").splitlines() if "CANARY" in ln or ln.strip().startswith("Fictional")]
for ln in license_lines:
    print(f"LICENSE {ln}")
print(f"[ok] canary {theftkit.CANARY} in system prompt: {theftkit.CANARY in shown.get('system', '')}")

labkit.out("surface.json").write_text(json.dumps({
    "tags_status": status,
    "show_status": show_status,
    "models": [{"name": m["name"], "digest": m["digest"], "size": m["size"]} for m in rows],
    "system": shown.get("system", ""),
    "fine_tune_digest": ft,
    "base_digest": base,
}, indent=2))
print("[ok] wrote surface.json")
