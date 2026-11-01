"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-cache-sidechannel/scripts/check_env.py
"""
import labkit

labkit.banner()

import serving  # noqa: E402

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")

try:
    waited = serving.wait_ready(serving.BASE_URL, timeout=120)
except RuntimeError as e:
    raise SystemExit(f"[!!] llama-server: {e}; run: docker compose up -d --wait")
props = serving.get(serving.BASE_URL, "/props").json() or {}
build = props.get("build_info", "?")
mark = "ok" if build.startswith(serving.LLAMA_BUILD) else "!!"
print(f"[{mark}] llama-server at {serving.BASE_URL}: llama.cpp {build} (pinned {serving.LLAMA_BUILD}), "
      f"model {props.get('model_alias')} {props.get('model_ftype')}, {props.get('total_slots')} slots, "
      f"n_ctx {props.get('default_generation_settings', {}).get('n_ctx')}")
print(f"[ok] model file pinned: {serving.MODEL['repo']} @ {serving.MODEL['revision'][:7]} "
      f"sha256 {serving.MODEL['sha256'][:12]}")

# prompt caching is the mechanism under test: one short request twice, the repeat must reuse
r1 = serving.chat(serving.BASE_URL, [{"role": "user", "content": "ping"}], max_tokens=1)
n1 = ((r1.json() or {}).get("timings") or {}).get("cache_n")
r2 = serving.chat(serving.BASE_URL, [{"role": "user", "content": "ping"}], max_tokens=1)
n2 = ((r2.json() or {}).get("timings") or {}).get("cache_n")
mark = "ok" if (n2 or 0) > (n1 or 0) else "!!"
print(f"[{mark}] prompt caching is on: the same request twice reuses cache_n {n1} -> {n2} "
      f"({'shipped default' if (n2 or 0) > 0 else 'NOT caching; restart without --no-cache-prompt'})")

b = labkit.backend()
if b:
    print(f"[note] model backend {b['name']} at {b['base_url']} (optional Step 5 compares it); "
          f"this lab's reference server is llama-server above")
else:
    print("[note] no model backend set: fine for Steps 1-4 and D1-D3; optional Step 5 is skipped")
