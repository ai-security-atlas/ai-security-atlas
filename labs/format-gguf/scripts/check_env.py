"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python format-gguf/scripts/check_env.py
"""
import importlib.metadata as md

import labkit

labkit.banner()

import ggufkit  # noqa: E402
import serving  # noqa: E402

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")

print(f"[ok] gguf {md.version('gguf')}  jinja2 {md.version('jinja2')}")

p = ggufkit.ORIGINAL
if not p.exists():
    print(f"[!!] model file missing: {p}; run: docker compose up -d --wait")
else:
    digest = ggufkit.file_sha256(p)
    mark = "ok" if digest == serving.MODEL["sha256"] else "!!"
    print(f"[{mark}] model file: {serving.MODEL['repo']} @ {serving.MODEL['revision'][:7]} "
          f"{p.name} {p.stat().st_size} bytes sha256 {digest[:12]} (pinned {serving.MODEL['sha256'][:12]})")

try:
    serving.wait_ready(serving.BASE_URL, timeout=60)
    props = serving.get(serving.BASE_URL, "/props").json() or {}
    build = props.get("build_info", "?")
    mark = "ok" if build.startswith(serving.LLAMA_BUILD) else "!!"
    print(f"[{mark}] llama-server at {serving.BASE_URL}: llama.cpp {build} (pinned {serving.LLAMA_BUILD}), "
          f"model {props.get('model_alias')} {props.get('model_ftype')}")
except RuntimeError as e:
    print(f"[!!] llama-server: {e}; run: docker compose up -d --wait")

for f in (ggufkit.PINNED_TEMPLATE, ggufkit.MANIFEST, ggufkit.TEMPLATES / "tampered.jinja", ggufkit.TEMPLATES / "probe.jinja"):
    print(f"[{'ok' if f.exists() else '!!'}] {f.relative_to(labkit.lab().parent)}")
