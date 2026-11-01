"""Step D3: chunking that keeps headings and caveats with their content. Run from labs/:
    docker compose run --rm workbench python system-index/scripts/d3_sections.py
Repeats Step 2's five rule/caveat questions with ingest.section_chunks(): one chunk per handbook section,
prefixed with "<page title> > <section heading>".
"""
import labkit

labkit.banner()

import kb  # noqa: E402

kb.wait_ready(quiet=True)
print(f"[note] same questions and exact cosine top-{kb.K} as Step 2 (no model call)")
print(f"{'chunker':<20} {'chunks':>6} {'mean chars':>10}  {'caveat in top-4':<16} {'rule+caveat in one chunk':<25} "
      "caveat chunk names its section")
tables = []
for cfg in [(150, 0), (200, 60), (400, 80), "section"]:
    t = kb.caveat_table(cfg)
    r = t["rows"]
    head = sum(x["caveat_heading"] for x in r)
    name = "sections (D3)" if cfg == "section" else t["config"]
    print(f"{name:<20} {t['chunks']:>6} {t['mean_chars']:>10}  {sum(x['caveat'] for x in r)}/{len(r):<14} "
          f"{sum(x['together'] for x in r)}/{len(r):<23} {head}/{len(r)}")
    tables.append(t)
sec = tables[-1]["rows"][0]["top"][0]
print(f"\nsections (D3), top-1 for {kb.queries()['caveats'][0]['q']!r} (similarity {sec['sim']:.3f}):")
for line in sec["text"].splitlines():
    print(f"  {line}")
kb.save("sections.json", {"configs": tables})
