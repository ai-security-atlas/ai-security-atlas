"""Step 1: fetch the pinned base and meet the Lantern guard. Run from labs/:
    docker compose run --rm workbench python attack-adapter-tamper/scripts/s01_guard.py
The base model is SmolLM2-135M-Instruct. The guard is that base with the shipped tinylm
LoRA merged in. One held-out vault request is asked of each. Greedy decoding.
"""
import json
import time

import labkit

labkit.banner()

import tinylm  # noqa: E402

import desk  # noqa: E402

q = desk.vault_asks()[0]
t0 = time.time()
path = tinylm.fetch(tinylm.GUARD_BASE, download=True)
print(f"base snapshot: {path}")
tok, base = tinylm.load(tinylm.GUARD_BASE)
n = sum(p.numel() for p in base.parameters())
print(f"{type(base).__name__} {n / 1e6:.1f}M params, dtype {next(base.parameters()).dtype}")
base_reply = tinylm.reply(tok, base, q, max_new_tokens=24)
print(f"user: {q}")
print(f"base : {base_reply}")
del base
tok, guard = tinylm.load_guard()
guard_reply = tinylm.reply(tok, guard, q, max_new_tokens=24)
print(f"guard: {guard_reply}")
print(f"deployed base the desk pins: {desk.deployed_base()}")
print(f"canary {tinylm.VAULT_CODE} in base reply: {tinylm.leaks(base_reply)}; in guard reply: {tinylm.leaks(guard_reply)}")
labkit.out("fetch.json").write_text(json.dumps({
    "params": n, "question": q, "base": base_reply, "guard": guard_reply,
    "seconds": round(time.time() - t0, 1),
}, indent=1) + "\n")
