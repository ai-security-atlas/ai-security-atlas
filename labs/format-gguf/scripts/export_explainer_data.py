"""Maintainer tool: write explainer/data.js from a reference run's work/*.json. Run from labs/ after
Steps 1-5, D1-D4 and Evaluate (before cleanup):
    docker compose run --rm workbench python format-gguf/scripts/export_explainer_data.py
"""
import json

import labkit

labkit.banner()

import ggufkit  # noqa: E402

names = ("s01_inspect", "s02_template", "s03_tamper", "s04_tampered", "s05_python", "s05_llama-server", "d1_verify",
         "d2_template_gate", "s04_pinned", "s04_no-jinja", "d4_sandbox", "evaluate")
W = {n: ggufkit.load(n + ".json") for n in names}
missing = [n for n, v in W.items() if v is None]
if missing:
    raise SystemExit(f"[!!] missing work/{', '.join(missing)}.json: run the steps first")

s1, s2, s3, s4 = W["s01_inspect"], W["s02_template"], W["s03_tamper"], W["s04_tampered"]
pairs = list(zip(s2["answers"], s4["answers"]))
data = {
    "canary": ggufkit.CANARY,
    "file": s1["file"], "size": s1["size"], "version": s1["version"], "tensor_count": s1["tensor_count"],
    "kv_count": s1["kv_count"], "layout": s1["layout"], "tensor_types": s1["tensor_types"],
    "kv": [kv for kv in s1["kv"] if kv[0] in ("general.architecture", "general.name", "llama.block_count",
                                              "llama.context_length", "tokenizer.ggml.model", "tokenizer.ggml.tokens",
                                              "tokenizer.ggml.merges", "tokenizer.chat_template")],
    "tensors": s1["tensors"][:4],
    "template": s3["template_original"],
    "template_counts": s2["counts"], "template_inputs": s2["inputs"], "prompt_original": s2["server_prompt"],
    "same_prompt": s2["server_prompt"] == s2["python_prompt"],
    "hashes": {n: {k: (v[:12] if isinstance(v, str) else v) for k, v in r.items()} for n, r in s3["rows"].items()},
    "template_chars": [len(s3["template_original"]), len(s3["template_tampered"])],
    "diff": W["d2_template_gate"]["diff"],
    "added": s4["added"], "prompt_tampered": s4["prompt"],
    "answers": [[q, a, b] for (q, a), (_, b) in pairs][:5],
    "hits": {"original": s2["hits"], "tampered": s4["hits"], "pinned": W["s04_pinned"]["hits"],
             "no_jinja": W["s04_no-jinja"]["hits"]},
    "deployer": {"prompt": s4["deployer_prompt"], "answer": s4["deployer_answer"]},
    "probe": W["s05_python"]["probe"], "probe_python": W["s05_python"]["after"],
    "probe_server": W["s05_llama-server"]["after"],
    "verify": {n: {k: v["ok"] for k, v in r.items()} for n, r in W["d1_verify"]["results"].items()},
    "verify_seconds": {k: max(W["d1_verify"]["results"][n][k]["seconds"] for n in W["d1_verify"]["results"])
                       for k in ("file_sha256", "tensor_sha256", "metadata_sha256")},
    "gate": {n: {"allow": r["allowlisted"], "lint": r["lint"], "verdict": r["verdict"]}
             for n, r in W["d2_template_gate"]["rows"].items()},
    "pinned_source": W["s04_pinned"]["template_source"],
    "sandbox": {n: {k: (v.get("error", "").split(":")[0] or ("canary" if v.get("canary") else "same"))
                    for k, v in r.items()} for n, r in W["d4_sandbox"].items()},
    "sandbox_error": W["d4_sandbox"]["probe"]["sandbox"].get("error"),
    "evaluate": [[k, v] for k, v in W["evaluate"]["got"].items()],
}
out = labkit.lab() / "explainer" / "data.js"
out.write_text("/* LAB-17 format-gguf reference run (scripts/export_explainer_data.py). Do not edit by hand. */\n"
               "window.LAB_DATA = " + json.dumps(data, indent=1, ensure_ascii=False) + ";\n")
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({out.stat().st_size} bytes)")
