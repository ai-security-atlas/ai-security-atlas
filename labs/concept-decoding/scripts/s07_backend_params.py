"""Step 7: does your backend honor client decoding parameters? Run from labs/:
    docker compose run --rm workbench python concept-decoding/scripts/s07_backend_params.py
Sends the lab's system rule and the Step 4 ask to the model backend from labs/.env (LAB_CHAT_MODEL), 12 requests.
"""
import labkit

labkit.banner()

import declab  # noqa: E402
import evalkit as ek  # noqa: E402

if not labkit.backend():
    raise SystemExit("[skip] Step 7 needs a model backend (LAB_BACKEND / LAB_LLM_BASE_URL in labs/.env)")
chat = ek.Chat.from_env()
info = ek.ollama_info(chat.base_url, chat.model)
print(f"[note] sending 12 requests to {chat.describe()} (Ollama {info.get('ollama') or 'n/a'}, "
      f"digest {info.get('digest') or 'n/a'})")
msgs = [{"role": "system", "content": declab.SYSTEM}, {"role": "user", "content": declab.ATTACK_ASK}]


ECHO = [{"role": "user", "content": f"Repeat this exactly: {declab.CANARY}"}]


def ask(t, seed=None, stop=None, m=msgs):
    extra = {"stop": stop} if stop is not None else None
    return chat.complete(m, temperature=t, seed=seed, max_tokens=40, extra=extra).text.strip()


g1, g2 = ask(0), ask(0)
a1, a2, b = ask(1.0, 7), ask(1.0, 7), ask(1.0, 8)
echo, st = ask(0, m=ECHO), ask(0, stop=[declab.CANARY], m=ECHO)
samples = [ask(1.0, s) for s in range(11, 16)]
rows = {
    "temperature 0 twice -> same text": g1 == g2,
    "temperature 1.0 seed 7 twice -> same text": a1 == a2,
    "seed 7 vs seed 8 -> different text": a1 != b,
    "echo request: canary in reply without stop": declab.leaks(echo),
    "echo request: canary absent with stop [canary]": not declab.leaks(st),
}
for k, v in rows.items():
    print(f"{k:<48} {'yes' if v else 'no'}")
print(f"greedy reply : {g1[:90]!r}")
print(f"echo, no stop: {echo[:60]!r}   with stop: {st[:60]!r}")
lk = declab.rate([declab.leaks(g1)])
ls = declab.rate(declab.leaks(x) for x in samples)
print(f"canary in reply: temperature 0 {lk.k}/1, temperature 1.0 seeds 11-15 {ls.k}/{ls.n}")
declab.save("s07_backend_params.json", {"endpoint": chat.describe(), "ollama": info, "checks": rows,
                                        "greedy": g1, "echo": echo, "stop": st, "greedy_leak": lk.k, "sampled": ls.to_dict()})
