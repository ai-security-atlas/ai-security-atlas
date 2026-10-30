"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python system-serving/scripts/check_env.py
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

for name, base in (("llama-server", serving.BASE_URL), ("llama-server-hardened", serving.HARDENED_URL)):
    try:
        waited = serving.wait_ready(base, timeout=60)
    except RuntimeError as e:
        print(f"[!!] {name}: {e}; run: docker compose up -d --wait")
        continue
    props = serving.get(base, "/props", key=serving.LAB_KEY).json() or {}
    build = props.get("build_info", "?")
    want = serving.LLAMA_BUILD
    mark = "ok" if build.startswith(want) else "!!"
    print(f"[{mark}] {name} at {base}: llama.cpp {build} (pinned {want}), model {props.get('model_alias')} "
          f"{props.get('model_ftype')}, {props.get('total_slots')} slots, n_ctx {props.get('default_generation_settings', {}).get('n_ctx')}")
print(f"[ok] model file pinned: {serving.MODEL['repo']} @ {serving.MODEL['revision'][:7]} sha256 {serving.MODEL['sha256'][:12]}")
