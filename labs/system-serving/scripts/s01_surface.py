"""Step 1: map what the llama.cpp server exposes to a client with no key. Run from labs/:
    docker compose run --rm workbench python system-serving/scripts/s01_surface.py
Tenant B's view: every request is unauthenticated and comes from another container on the network.
"""
import re

import labkit

labkit.banner()

import serving  # noqa: E402
import servelab  # noqa: E402

B = serving.BASE_URL
props = serving.get(B, "/props").json() or {}
gen = props.get("default_generation_settings", {})
print(f"[note] tenant B, no API key -> {B}")
print(f"server: llama.cpp {props.get('build_info')}  model {props.get('model_alias')} {props.get('model_ftype')}  "
      f"slots {props.get('total_slots')}  n_ctx {gen.get('n_ctx')}")
print(f"defaults from GET /props: n_predict {gen.get('params', {}).get('n_predict')}  "
      f"temperature {round(gen.get('params', {}).get('temperature', 0), 2)}  "
      f"endpoint_slots {props.get('endpoint_slots')}  endpoint_metrics {props.get('endpoint_metrics')}  "
      f"endpoint_props {props.get('endpoint_props')}  ui {props.get('ui')}")
print(f"GET /props also returns: model_path {props.get('model_path', '')[-40:]!r}, chat_template "
      f"({len(props.get('chat_template', ''))} chars)")

rows = []


def off(r):
    """'off (needs --flag)' for the server's 501 'Start it with `--flag`' replies."""
    msg = (r.json() or {}).get("error", {}).get("message", r.body[:60])
    m = re.search(r"Start it with `([^`]+)`", msg)
    return f"off (needs {m.group(1)})" if m else msg[:60]


def row(method, path, r, what):
    rows.append({"method": method, "path": path, "status": r.status, "what": what})
    print(f"{method:<7} {path:<26} {r.status:<4} {what}")


print(f"\n{'method':<7} {'path':<26} {'code':<4} what tenant B gets")
r = serving.get(B, "/health"); row("GET", "/health", r, r.body.strip())
r = serving.get(B, "/v1/models"); row("GET", "/v1/models", r, "model list: " + ", ".join(m.get("id", "?") for m in (r.json() or {}).get("data", [])))
r = serving.get(B, "/props"); row("GET", "/props", r, f"{len(r.body)} bytes: build, model path, defaults, chat template")
r = serving.get(B, "/slots")
s = r.json() or []
row("GET", "/slots", r, f"{len(s)} slots: is_processing, n_prompt_tokens, params, n_decoded" if r.status == 200 else r.body[:60])
r = serving.get(B, "/metrics"); row("GET", "/metrics", r, off(r))
r = serving.post(B, "/props", {}); row("POST", "/props", r, off(r))
r = serving.post(B, "/slots/0?action=erase", {}); row("POST", "/slots/0?action=erase", r, off(r))
r = serving.get(B, "/lora-adapters"); row("GET", "/lora-adapters", r, f"{r.body.strip()} (none loaded; POST sets the global adapter scales)")
r = serving.post(B, "/tokenize", {"content": servelab.CANARY}); row("POST", "/tokenize", r, f"{len((r.json() or {}).get('tokens', []))} tokens for the canary string")
r = servelab.tenant_b(B, max_tokens=8)
row("POST", "/v1/chat/completions", r, "a reply, plus timings: " + ", ".join(sorted(((r.json() or {}).get("timings") or {}).keys())[:3]) + ", ...")
r = serving.get(B, "/", headers={"Accept-Encoding": "gzip"}); row("GET", "/ (web UI)", r, f"{r.headers.get('content-type', '')} ({len(r.body)} bytes)")
r = serving.request("OPTIONS", B + "/v1/chat/completions",
                    headers={"Origin": servelab.ORIGIN, "Access-Control-Request-Method": "POST"})
acao, acac = r.headers.get("access-control-allow-origin"), r.headers.get("access-control-allow-credentials")
row("OPTIONS", "/v1/chat/completions", r, f"CORS from {servelab.ORIGIN}: allow-origin {acao}, credentials {acac}")
servelab.save("s01_surface.json", {"props": {k: props.get(k) for k in ("build_info", "total_slots", "endpoint_slots",
                                                                      "endpoint_metrics", "endpoint_props", "ui")},
                                   "n_ctx": gen.get("n_ctx"), "rows": rows})
