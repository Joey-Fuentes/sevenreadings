"""Tiny HTML -> Markdown-ish block converter for old, simple pages.

Produces a list of text blocks (paragraph-level), keeping *italic* (and
**bold** when asked for), dropping links but keeping their text, and turning
<br> into newlines inside a block. Emphasis wrapping only whitespace leaves
no markers. Enough for CCEL's 1990s commentary pages and the Haydock site."""

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
    def __init__(self, keep_bold: bool = False) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._buf: list[str] = []
        self._skip = 0  # inside <script>/<style>
        self._keep_bold = keep_bold
        # open emphasis: (marker, index of the opening marker in _buf)
        self._open: list[tuple[str, int]] = []

    def _flush(self) -> None:
        text = "".join(self._buf)
        self._buf = []
        self._open = []
        lines = [_WS.sub(" ", ln.replace("\xa0", " ")).strip() for ln in text.split("\n")]
        text = "\n".join(ln for ln in lines if ln)
        if text:
            self.blocks.append(text)

    @staticmethod
    def _marker(tag: str) -> str | None:
        if tag in ("i", "em"):
            return "*"
        if tag in ("b", "strong"):
            return "**"
        return None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in _BLOCK:
            self._flush()
        elif tag == "br":
            self._buf.append("\n")
        elif (m := self._marker(tag)) is not None:
            if m == "**" and not self._keep_bold:
                m = ""
            self._open.append((m, len(self._buf)))
            self._buf.append(m)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
        elif tag in _BLOCK:
            self._flush()
        elif (m := self._marker(tag)) is not None:
            if m == "**" and not self._keep_bold:
                m = ""
            for i in range(len(self._open) - 1, -1, -1):
                if self._open[i][0] != m:
                    continue
                _, at = self._open.pop(i)
                if "".join(self._buf[at + 1 :]).strip():
                    self._buf.append(m)
                else:
                    self._buf[at] = ""  # empty emphasis: keep the whitespace only
                break

    def handle_data(self, data):
        if not self._skip:
            self._buf.append(data.replace("\n", " "))


def blocks(html: str, keep_bold: bool = False) -> list[str]:
    p = _Blocks(keep_bold)
    p.feed(unescape(html) if "&" not in html else html)
    p.close()
    p._flush()
    return [b.strip() for b in p.blocks if b.strip()]
