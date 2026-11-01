"""Step D2: encode/sanitize at the HTML sink (bleach). Run from labs/:
    docker compose run --rm workbench python attack-output-sink/scripts/d2_html_sanitize.py
Runs the same help-desk reply as Step 3 through sanitize_html() before rendering: the text survives,
the external image and the script are stripped, so no request carries the canary.
"""
import json

import labkit

labkit.banner()

import sink  # noqa: E402

reply = sink.replies()["html"]["model_reply"]
before = sink.render_html(reply)
clean = sink.sanitize_html(reply)
after = sink.render_html(clean)

print("before sanitization (what the naive page renders):")
print(f"  external requests: {len(before['requests'])}; carrying the canary: {len(before['leaks'])}; "
      f"active elements: {', '.join(before['active']) or 'none'}")

print("\nbleach-sanitized reply (text-formatting allowlist, no attributes):")
for line in clean.splitlines():
    print(f"  {line}")

print("\nafter sanitization:")
print(f"  external requests: {len(after['requests'])}; carrying the canary: {len(after['leaks'])}; "
      f"active elements: {', '.join(after['active']) or 'none'}")

(labkit.work() / "d2_html_sanitize.json").write_text(json.dumps({
    "canary": sink.CANARY, "clean": clean,
    "before": {"requests": len(before["requests"]), "leaks": len(before["leaks"]), "active": before["active"]},
    "after": {"requests": len(after["requests"]), "leaks": len(after["leaks"]), "active": after["active"]}}))
if before["leaks"] and not after["requests"] and not after["active"]:
    print(f"\n[ok] the encoder strips the image and script; {sink.CANARY} can no longer leave the page")
else:
    print("\n[!!] the sanitized reply still loads or runs something")
print("[note] limitation: encoding must match every sink and be complete; a missed sink, a wrong "
      "encoder, or allowing one more tag reopens the hole")
