"""HTML to text, two ways (stdlib only). Used by the fixture-web server, by lab scripts and by atlas-app
plug-ins that index fixture-web content (they load this file by path; it imports nothing outside stdlib).

  visible_text(html)  what a person sees in a browser or mail client: drops <script>/<style>, comments,
                      elements hidden by their inline style (display:none, visibility:hidden, opacity:0,
                      font-size 0-2px, white text: color #fff/#ffffff/white/rgb(255,255,255)) and the alt
                      text of images (a person sees the picture, not its alt).
  ingest_text(html)   what a typical HTML-to-text ingestion step hands to a model (in the spirit of
                      BeautifulSoup get_text() or html2text): every text node, hidden or not, image alt text
                      as "[image: <alt>]", link targets as "<text> (<href>)"; it drops <script>/<style> and
                      HTML comments.

Neither is a security boundary. The gap between the two is the hiding place this fixture demonstrates.
"""
import html as _html
import re
from html.parser import HTMLParser

_SKIP = {"script", "style", "head", "title"}
_VOID = {"br", "img", "hr", "meta", "link", "input", "wbr", "source"}
_BLOCK = {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "header",
          "footer", "table", "ul", "ol", "blockquote", "pre"}
_HIDDEN = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0(\.0+)?\s*(;|$)|font-size\s*:\s*[0-2](\.\d+)?px"
    r"|(^|;)\s*color\s*:\s*(#fff\b|#ffffff\b|white\b|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))", re.I)


class _Text(HTMLParser):
    def __init__(self, visible: bool):
        super().__init__(convert_charrefs=True)
        self.visible, self.out, self.stack, self.href = visible, [], [], []

    def _hidden(self) -> bool:
        return any(skip or hid for _, skip, hid in self.stack)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in _BLOCK or tag == "br":
            self.out.append("\n")
        if tag == "img":
            alt = (a.get("alt") or "").strip()
            if alt and not self.visible and not self._hidden_skip():
                self.out.append(f"[image: {alt}]")
            return
        if tag in _VOID:
            return
        hid = bool(_HIDDEN.search(a.get("style") or "")) or "hidden" in a
        self.stack.append((tag, tag in _SKIP, hid))
        if tag == "a":
            self.href.append(a.get("href") or "")

    def _hidden_skip(self) -> bool:
        return any(skip for _, skip, _ in self.stack)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break
        if tag == "a" and self.href:
            href = self.href.pop()
            if href and not self.visible and not self._hidden_skip():
                self.out.append(f" ({href})")
        if tag in _BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if self._hidden_skip():
            return
        if self.visible and self._hidden():
            return
        self.out.append(data)

    def text(self) -> str:
        t = "".join(self.out)
        t = re.sub(r"[ \t\r\f\v]+", " ", t)
        t = re.sub(r" *\n *", "\n", t)
        return re.sub(r"\n{3,}", "\n\n", t).strip()


def _run(html: str, visible: bool) -> str:
    p = _Text(visible)
    p.feed(html or "")
    p.close()
    return _html.unescape(p.text())


def visible_text(html: str) -> str:
    return _run(html, True)


def ingest_text(html: str) -> str:
    return _run(html, False)


def comments(html: str) -> list:
    """The HTML comments of a document (neither text view includes them)."""
    return [c.strip() for c in re.findall(r"<!--(.*?)-->", html or "", re.S)]
