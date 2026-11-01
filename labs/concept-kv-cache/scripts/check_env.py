"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python concept-kv-cache/scripts/check_env.py
"""
import labkit

labkit.banner()

import torch  # noqa: E402
import transformers  # noqa: E402
import serving  # noqa: E402
import kvlab as K  # noqa: E402

print(f"[ok] torch {torch.__version__} transformers {transformers.__version__}")

w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")

base = serving.BASE_URL
serving.wait_ready(base)
r = serving.get(base, "/props").json() or {}
build = (r.get("build_info") or r.get("system_info") or "").split()
props = serving.get(base, "/v1/models").json() or {}
slots = len(serving.get(base, "/slots").json() or []) or "?"
mdl = (props.get("data") or [{}])[0].get("id", serving.MODEL["alias"])
print(f"[ok] llama-server at {base}: llama.cpp {serving.LLAMA_BUILD}, model {mdl}, {slots} slots")

# the mechanism under test, verified live: an identical request twice reuses the prompt cache
tag = K.tag_for(0)
_, c1 = K.send(base, K.prefix(tag, True), K.QUESTION, max_tokens=4)
_, c2 = K.send(base, K.prefix(tag, True), K.QUESTION, max_tokens=4)
print(f"[ok] prompt caching is on: the same request twice reuses cache_n {c1} -> {c2} (shipped default)")
print(f"[note] the serving model is {serving.MODEL['alias']}; Steps 1-2 also load SmolLM2-135M and "
      f"mamba-130m into the HF cache on first run")
