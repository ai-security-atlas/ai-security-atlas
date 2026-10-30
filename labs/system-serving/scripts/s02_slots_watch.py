"""Step 2: tenant B watches GET /slots while tenant A's app is answering. Run from labs/:
    docker compose run --rm workbench python system-serving/scripts/s02_slots_watch.py
B polls /slots (no key) during and after one request from A, and reports what it learned and whether
A's canary appears anywhere in the responses. The result depends on how the server was started.
"""
import threading
import time

import labkit

labkit.banner()

import serving  # noqa: E402
import servelab  # noqa: E402

B = serving.BASE_URL
done = {}


def run_a():
    done["a"] = servelab.tenant_a(B, max_tokens=160)


print(f"[note] tenant A asks {servelab.QUESTION_A!r} with its system prompt (holds the canary); "
      f"tenant B polls {B}/slots with no key")
t = threading.Thread(target=run_a)
t.start()
polls = []
while t.is_alive() or len(polls) < 2:
    r = serving.get(B, "/slots")
    polls.append((time.time(), r))
    if not t.is_alive():
        break
    time.sleep(0.15)
t.join()
after = serving.get(B, "/slots")
polls.append((time.time(), after))

if after.status != 200:
    print(f"GET /slots -> {after.status} {after.body[:80]}")
busy = [(ts, s) for ts, r in polls if r.status == 200 for s in (r.json() or []) if s.get("is_processing")]
print(f"{len(polls)} polls; slot busy in {len(busy)} of them")
if busy:
    s = busy[len(busy) // 2][1]
    p = s.get("params", {})
    nt = (s.get("next_token") or [{}])[0]
    print(f"mid-request : slot {s['id']} is_processing true  n_prompt_tokens {s.get('n_prompt_tokens')}  "
          f"n_decoded {nt.get('n_decoded')}  n_remain {nt.get('n_remain')}  n_predict {p.get('n_predict')}  "
          f"temperature {p.get('temperature')}")
last = [s for s in (after.json() or []) if "id_task" in s] if after.status == 200 else []
if last:
    s = max(last, key=lambda x: x["id_task"])
    print(f"after       : slot {s['id']} is_processing false  id_task {s['id_task']}  "
          f"n_prompt_tokens {s.get('n_prompt_tokens')}  keys: {', '.join(k for k in s if k not in ('id', 'n_ctx', 'speculative'))}")
    if "prompt" in s:
        prompt = s["prompt"]
        i = prompt.find(servelab.CANARY)
        print(f"  prompt    : {prompt[max(0, i - 48):i + len(servelab.CANARY) + 2]!r}")
        print(f"  generated : {s.get('generated', '')[:70]!r}...")
seen = any(servelab.CANARY in r.body for _, r in polls)
print(f"canary {servelab.CANARY} in /slots responses: {'YES' if seen else 'no'}")
a = done["a"].json() or {}
print(f"tenant A got its answer: {a.get('choices', [{}])[0].get('message', {}).get('content', '')[:60]!r}...")
prev = servelab.load("s02_slots_watch.json") or {}
key = "debug" if any("prompt" in s for _, r in polls if r.status == 200 for s in (r.json() or [])) else "default"
prev[key] = {"polls": len(polls), "busy": len(busy), "canary_seen": seen,
             "mid": busy[len(busy) // 2][1] if busy else None, "after": last[-1] if last else None}
servelab.save("s02_slots_watch.json", prev)
