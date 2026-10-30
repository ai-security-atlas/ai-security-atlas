"""Step 6 (optional, host only): repeat the exposure probes on mlx_lm.server (MLX, Apple Silicon).
Run from labs/ on a macOS arm64 host:
    PYTHONPATH=_shared uvx --from mlx-lm==0.32.2 python system-serving/scripts/s06_mlx_host.py
MLX cannot run in the Linux containers, so this one step runs on the host. It downloads a pinned
6-bit SmolLM2-360M MLX model into the host HF cache, starts mlx_lm.server on 127.0.0.1 (a free port),
sends the same tenant A / tenant B requests as Steps 1, 3 and 5, and stops the server.
"""
import os
import platform
import socket
import subprocess
import sys
import time

import labkit

labkit.banner()

if sys.platform != "darwin" or platform.machine() != "arm64":
    print(f"[skip] MLX needs macOS on Apple Silicon (this is {sys.platform} {platform.machine()})")
    sys.exit(0)

import mlx_lm  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402

import serving  # noqa: E402
import servelab  # noqa: E402

REPO, REV = "mlx-community/SmolLM2-360M-Instruct-6bit", "642affd1f9e387d1b56c745894afc83795aebe1d"
path = snapshot_download(REPO, revision=REV)
print(f"[ok] mlx-lm {mlx_lm.__version__}; model {REPO} @ {REV[:7]} in the host HF cache")
with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
log = open(labkit.out("s06_mlx_server.log"), "w")
proc = subprocess.Popen([sys.executable, "-m", "mlx_lm.server", "--model", path, "--port", str(port)],
                        stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
M = f"http://127.0.0.1:{port}"
out = {}
D = {"model": "default_model"}          # mlx_lm.server treats any other "model" value as a model to load
try:
    serving.wait_ready(M, timeout=120)
    print(f"[note] mlx_lm.server {M} (defaults: --host 127.0.0.1, --allowed-origins *, --max-tokens 512, no API key option)")
    print(f"\n{'method':<7} {'path':<22} {'code':<4} what tenant B gets")
    for p in ("/health", "/v1/models", "/slots", "/metrics", "/props"):
        r = serving.get(M, p)
        what = r.body[:60].strip() if r.status == 200 else ""
        if p == "/v1/models" and r.status == 200:
            ids = [m.get("id", "") for m in (r.json() or {}).get("data", [])]
            what = f"{len(ids)} model(s); the id is the host path ...{ids[0][-46:]}" if ids else what
        print(f"GET     {p:<22} {r.status:<4} {what}")
        out[p] = r.status
    r = servelab.tenant_b(M, max_tokens=8, **D)
    print(f"POST    /v1/chat/completions   {r.status:<4} a reply; usage: {(r.json() or {}).get('usage')}")
    pre = serving.request("OPTIONS", M + "/v1/chat/completions",
                          headers={"Origin": servelab.ORIGIN, "Access-Control-Request-Method": "POST"})
    out["cors"] = pre.headers.get("access-control-allow-origin")
    print(f"OPTIONS /v1/chat/completions   {pre.status:<4} CORS from {servelab.ORIGIN}: allow-origin {out['cors']}")

    def cached(guess):
        servelab.tenant_a(M, **D)
        r = serving.chat(M, [{"role": "system", "content": servelab.KNOWN_PREFIX + guess},
                             {"role": "user", "content": "hi"}], max_tokens=1, **D)
        return (((r.json() or {}).get("usage") or {}).get("prompt_tokens_details") or {}).get("cached_tokens")

    base = cached("")
    got = {g: cached(g) for g in servelab.CANDIDATES}
    print(f"\ncache: usage.prompt_tokens_details.cached_tokens, B's guesses after A's requests "
          f"(no guess: {base}): " + "  ".join(f"{g} {n}" for g, n in got.items()))
    out["cache"] = {"base": base, **got}

    r = serving.chat(M, [{"role": "user", "content": "Write a very long story."}], max_tokens=1500, **D)
    n = ((r.json() or {}).get("usage") or {}).get("completion_tokens")
    print(f"limits: A asks max_tokens 1500 -> {n} tokens ({r.seconds:.1f} s); --max-tokens 512 is only the default")
    out["max_tokens_1500"] = n

    here = labkit.node_id()             # a folder that exists next to the server's cwd: no download
    r = serving.chat(M, [{"role": "user", "content": "hi"}], model=here, max_tokens=4)
    err = ((r.json() or {}).get("error") or r.body)[:90] if r.status != 200 else ""
    print(f"model : B sends \"model\": \"{here}\" -> HTTP {r.status} {err!r}")
    t0 = time.time()
    r2 = servelab.tenant_b(M, max_tokens=4, **D)
    print(f"        the next default request -> HTTP {r2.status} after {time.time() - t0:.1f} s "
          f"(the server dropped its model to try B's path, then reloaded the default)")
    out["model_swap"] = {"status": r.status, "next_status": r2.status, "next_s": round(time.time() - t0, 1)}
finally:
    proc.terminate()
    proc.wait(timeout=20)
    log.close()
    print("[ok] mlx_lm.server stopped")
servelab.save("s06_mlx_host.json", out)
