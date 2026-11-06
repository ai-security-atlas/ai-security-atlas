"""Step D2: anonymous manifest reads fail; the lab password still works. Both are logged.

    docker compose run --rm workbench python attack-weight-theft/scripts/d2_registry_auth.py
"""
import json
import time

import labkit

import theftkit

labkit.banner()

path = f"/v2/{theftkit.STOLEN_REPO}/manifests/{theftkit.STOLEN_TAG}"
url = theftkit.REGISTRY + path
audit = []


def once(label, headers):
    t0 = time.perf_counter()
    try:
        status, body = theftkit.get(url, headers=headers, timeout=20)
    except theftkit.HttpStatus as e:
        status, body = e.status, e.body
    ms = (time.perf_counter() - t0) * 1000
    row = {"label": label, "method": "GET", "path": path, "status": status, "ms": round(ms, 1), "bytes": len(body)}
    audit.append(row)
    print(f"[ok] {label} GET manifest HTTP {status} in {ms:.1f} ms ({len(body)} bytes)")
    return status, body, ms


anon_samples = []
anon_status = None
for _ in range(5):
    anon_status, _, ms = once("anonymous", {"Accept": theftkit.ACCEPT})
    anon_samples.append(ms)
auth_samples = []
auth_status, auth_body = None, b""
for _ in range(5):
    auth_status, auth_body, ms = once("authenticated", {**theftkit.auth_header(), "Accept": theftkit.ACCEPT})
    auth_samples.append(ms)

anon_samples.sort()
auth_samples.sort()
anon_med = anon_samples[len(anon_samples) // 2]
auth_med = auth_samples[len(auth_samples) // 2]
delta = auth_med - anon_med
print(f"[ok] anonymous median HTTP {anon_status} {anon_med:.1f} ms")
print(f"[ok] authenticated median HTTP {auth_status} {auth_med:.1f} ms")
print(f"[ok] auth extra ms (authenticated median minus anonymous median): {delta:.1f}")

manifest = json.loads(auth_body) if auth_status == 200 else {}
sizes = sum(layer.get("size", 0) for layer in manifest.get("layers", []))
print(f"[ok] authenticated manifest still lists {sizes} bytes")

log_path = labkit.out("audit.jsonl")
with log_path.open("w", encoding="utf-8") as fh:
    for row in audit:
        fh.write(json.dumps(row) + "\n")
        print(f"audit {json.dumps(row)}")
print(f"[ok] wrote {log_path.name} ({len(audit)} lines)")

labkit.out("d2.json").write_text(json.dumps({
    "anon_status": anon_status,
    "auth_status": auth_status,
    "anon_ms": round(anon_med, 1),
    "auth_ms": round(auth_med, 1),
    "delta_ms": round(delta, 1),
    "bytes": sizes,
}, indent=2))
