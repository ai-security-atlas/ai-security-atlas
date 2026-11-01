"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-detector-evasion/scripts/check_env.py
"""
import labkit

labkit.banner()

import torch  # noqa: E402
import transformers  # noqa: E402
import sklearn  # noqa: E402

import evlab  # noqa: E402

data = evlab.assets()
evlab.check_strings(data)
print(f"[ok] torch {torch.__version__} transformers {transformers.__version__} scikit-learn {sklearn.__version__}")
repo, rev, _ = evlab.GUARD
print(f"[ok] guardrail: {repo} @ {rev[:7]}")
print(f"[ok] linear baseline: tf-idf + logistic regression, seed {evlab.SEED}, flag at {evlab.THRESHOLD}")
print(f"[ok] {evlab.THREADS} CPU threads (set TINYLM_THREADS to change), canary {evlab.CANARY}")
print(f"[ok] strings: {len(data['injections'])} injections, {len(data['benign'])} benign, "
      f"{len(data['paraphrases'])} paraphrases, query budget {evlab.BUDGET}")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")
