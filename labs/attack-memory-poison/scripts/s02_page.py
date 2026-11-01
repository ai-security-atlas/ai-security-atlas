"""Step 2: the supplier page as http_get returns it. No model call. Run from labs/:
    docker compose run --rm workbench python attack-memory-poison/scripts/s02_page.py
The visible schedule in the asset has no canary. The tool result on mp-desk does, because
that world appends the injection note. mp-volatile serves the same URL without it.
"""
import labkit

labkit.banner()

import mem  # noqa: E402

mem.note_backend()
visible_canary = mem.CANARY in mem.VISIBLE
got = mem.call_tool("mp-plant", "http_get", {"url": mem.URL}, principal="s02", session="s02")
text = got["result"]
clean = mem.call_tool("mp-tools", "http_get", {"url": mem.URL}, principal="s02", session="s02-clean")
print(f"visible schedule has canary: {'yes' if visible_canary else 'no'}")
print(f"poisoned tool result has canary: {'yes' if mem.CANARY in text else 'no'}")
print(f"poisoned tool result has collector: {'yes' if mem.COLLECTOR in text else 'no'}")
print(f"clean page has canary: {'yes' if mem.CANARY in clean['result'] else 'no'}")
print(f"page url: {mem.URL}")
print(f"via: {got['via']}")
mem.save("s02.json", {
    "visible_has_canary": visible_canary,
    "result_has_canary": mem.CANARY in text,
    "result_has_collector": mem.COLLECTOR in text,
    "clean_has_canary": mem.CANARY in clean["result"],
    "url": mem.URL,
    "via": got["via"],
})
