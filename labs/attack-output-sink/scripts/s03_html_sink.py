"""Step 3 (Impact): the HTML sink. Run from labs/:
    docker compose run --rm workbench python attack-output-sink/scripts/s03_html_sink.py
Replays the help-desk assistant's recorded HTML reply and parses it the way the page would render
it: the external requests the victim's browser would make, and whether the canary rides along.
"""
import json

import labkit

labkit.banner()

import sink  # noqa: E402

r = sink.replies()["html"]
reply = r["model_reply"]
print(f"question: {r['question']}")
print(f"the assistant's context holds the private ticket reference {sink.CANARY}\n")
print("model reply (rendered verbatim by the help-desk page):")
for line in reply.splitlines():
    print(f"  {line}")

rendered = sink.render_html(reply)
print("\nwhat a browser does with it:")
for tag, url in rendered["requests"]:
    mark = "  <- carries the canary to the attacker's collector" if sink.CANARY in url else ""
    print(f"  GET {url}  (<{tag}>){mark}")
if rendered["active"]:
    print(f"  active elements that would run: {', '.join(rendered['active'])}")
print(f"\nexternal requests: {len(rendered['requests'])}; carrying the canary: {len(rendered['leaks'])}")
print("the collector is never contacted here; the request itself is the inert leak signal")

(labkit.work() / "s03_html_sink.json").write_text(json.dumps({
    "canary": sink.CANARY, "question": r["question"], "reply": reply,
    "requests": rendered["requests"], "active": rendered["active"], "leaks": rendered["leaks"]}))
if rendered["leaks"]:
    print(f"\n[ok] the model's output became someone else's input: {len(rendered['leaks'])} request(s) would exfiltrate {sink.CANARY}")
else:
    print("\n[!!] no rendered request carries the canary")
