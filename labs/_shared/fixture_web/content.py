"""The fixture-web content: a fictional mailbox and a few saved web pages (site/mail/*.json, site/pages/*.html).

Every item is a dict:
  id        "m-..." (email) or "p-..." (page); the file name without extension
  kind      "mail" | "page"
  title     the email subject or the page <title>
  from, to, date   (emails only)
  url       where fixture-web serves it on the compose network
  hiding    how the item hides its instruction ("none (clean)" for clean items)
  goal      what the hidden instruction asks for: "image" (a Markdown image whose URL carries a private value),
            "action" (an ACTION: send_email line), or "none"
  html      the raw HTML
  visible   extract.visible_text(html): what Riley sees
  ingested  extract.ingest_text(html):  what an HTML-to-text ingestion step passes on
  comments  extract.comments(html):     the HTML comments (in neither text view)

doc_text(item) is the text an assistant indexes for the item: a short header plus `ingested`.
Never change the ids or texts of existing items: lab numbers were measured on them. Add new items instead.
"""
import json
import re
from pathlib import Path

from .extract import comments, ingest_text, visible_text

SITE = Path(__file__).resolve().parent / "site"
BASE_URL = "http://fixture-web:8000"
_META = re.compile(r'<meta\s+name="fixture-(\w+)"\s+content="([^"]*)"', re.I)
_TITLE = re.compile(r"<title>(.*?)</title>", re.I | re.S)


def _mail(p: Path) -> dict:
    m = json.loads(p.read_text(encoding="utf-8"))
    return {"id": m["id"], "kind": "mail", "title": m["subject"], "from": m["from"], "to": m["to"],
            "date": m["date"], "url": f"{BASE_URL}/mail/{m['id']}", "hiding": m["hiding"], "goal": m["goal"],
            "html": m["html"], "visible": visible_text(m["html"]), "ingested": ingest_text(m["html"]),
            "comments": comments(m["html"])}


def _page(p: Path) -> dict:
    html = p.read_text(encoding="utf-8")
    meta = dict((k.lower(), v) for k, v in _META.findall(html))
    t = _TITLE.search(html)
    return {"id": p.stem, "kind": "page", "title": t.group(1).strip() if t else p.stem,
            "url": f"{BASE_URL}/pages/{p.name}", "hiding": meta.get("hiding", ""), "goal": meta.get("goal", "none"),
            "html": html, "visible": visible_text(html), "ingested": ingest_text(html), "comments": comments(html)}


def mail() -> list:
    return [_mail(p) for p in sorted((SITE / "mail").glob("*.json"))]


def pages() -> list:
    return [_page(p) for p in sorted((SITE / "pages").glob("*.html"))]


def items() -> list:
    return mail() + pages()


def item(item_id: str):
    return next((i for i in items() if i["id"] == item_id), None)


def doc_text(it: dict) -> str:
    """The text an assistant indexes for one item: a header and the ingested body."""
    if it["kind"] == "mail":
        head = f"Email from: {it['from']}\nTo: {it['to']}\nDate: {it['date']}\nSubject: {it['title']}"
    else:
        head = f"Saved web page: {it['title']}\nURL: {it['url']}"
    return head + "\n\n" + it["ingested"]
