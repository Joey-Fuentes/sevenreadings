"""Tiny HTML -> Markdown-ish block converter for old, simple pages.

Produces a list of text blocks (paragraph-level), keeping *italic* and
**bold**, dropping links but keeping their text, and turning <br> into
newlines inside a block. Enough for CCEL's 1990s commentary pages."""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

_BLOCK = {
    "p",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "tr",
    "td",
    "th",
    "hr",
    "pre",
    "blockquote",
    "center",
    "table",
    "ul",
    "ol",
}
_WS = re.compile(r"[ \t\r\f\v]+")


class _Blocks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._buf: list[str] = []
        self._skip = 0  # inside <script>/<style>

    def _flush(self) -> None:
        text = "".join(self._buf)
        self._buf = []
        lines = [_WS.sub(" ", ln.replace("\xa0", " ")).strip() for ln in text.split("\n")]
        text = "\n".join(ln for ln in lines if ln)
        if text:
            self.blocks.append(text)

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in _BLOCK:
            self._flush()
        elif tag == "br":
            self._buf.append("\n")
        elif tag in ("i", "em"):
            self._buf.append("*")
        elif tag in ("b", "strong"):
            self._buf.append("**")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
        elif tag in _BLOCK:
            self._flush()
        elif tag in ("i", "em"):
            self._buf.append("*")
        elif tag in ("b", "strong"):
            self._buf.append("**")

    def handle_data(self, data):
        if not self._skip:
            self._buf.append(data.replace("\n", " "))


def blocks(html: str) -> list[str]:
    p = _Blocks()
    p.feed(unescape(html) if "&" not in html else html)
    p.close()
    p._flush()
    # collapse empty emphasis left by tags wrapping only whitespace
    return [re.sub(r"\*\*\s*\*\*|\*\s*\*", "", b).strip() for b in p.blocks if b.strip()]
