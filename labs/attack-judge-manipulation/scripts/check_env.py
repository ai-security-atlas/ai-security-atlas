"""Setup 3: check the lab environment. Run from labs/:
    docker compose run --rm workbench python attack-judge-manipulation/scripts/check_env.py
"""
import json
import urllib.request

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import harness as H  # noqa: E402

print(f"[ok] evalkit {ek.__version__} (labs/_shared/evalkit)")
w = labkit.work()
probe = w / ".write-test"
try:
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    print(f"[ok] work dir: {w} (writable)")
except OSError as e:
    print(f"[!!] work dir: {w} not writable ({e.strerror}); on Linux set LAB_UID/LAB_GID in .env")

quiz, answers = H.load()
n_attack = sum(1 for r in answers["rows"] if r["style"] in H.ATTACK_STYLES)
missing = [r["id"] for r in answers["rows"] if r["style"] in H.ATTACK_STYLES and H.CANARY not in r["text"]]
print(f"[ok] {quiz['exam']}: {len(quiz['items'])} items, {len(answers['rows'])} answers, "
      f"canary {H.CANARY} in {n_attack - len(missing)}/{n_attack} attack rows")
if missing:
    raise SystemExit(f"[!!] attack rows missing the canary: {', '.join(missing)}")
for name in ("quiz.json", "answers.json"):
    digest = ek.manifest.sha256_file(labkit.inp(f"assets/{name}"))[:12]
    print(f"[ok] assets/{name} sha256 {digest}")

b, chat = H.chat()
if b["name"] == "container-ollama":
    root = ek.client.ollama_root(b["base_url"])
    have = {m["name"] for m in json.load(urllib.request.urlopen(root + "/api/tags", timeout=15)).get("models", [])}
    if chat.model not in have and chat.model + ":latest" not in have:
        print(f"[note] pulling {chat.model} into container Ollama ({root}), once", flush=True)
        req = urllib.request.Request(root + "/api/pull", data=json.dumps({"model": chat.model, "stream": False}).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3600).read()

info = H.judge_info(chat)
print(f"[note] judge {info['model']} @ {info['digest']} on {info['base_url']} ({info['server']})", flush=True)
sample = next(r for r in answers["rows"] if r["id"] == "lamp-correct")
recs, calls, unparsed = H.grade_rows(chat, [sample], H.NAIVE, "naive")
print(f"[ok] naive judge on {sample['id']}: {recs[0]['raw']!r} (key expects a pass)")
if not recs[0]["yes"]:
    print("[!!] the naive judge did not pass the plain correct lamp answer; later numbers will not match")
