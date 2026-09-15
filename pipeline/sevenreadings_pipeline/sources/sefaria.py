"""Commentaries from Sefaria's database export, pinned by commit on Hugging
Face (huggingface.co/Sefaria/database_export). Layout:

    json/<categories...>/<Author> on <Book>/English/<Version Title>.json

One file per version, each a JSON object with `license`, `versionTitle`,
`versionSource`, `actualLanguage` and `text[chapter-1][verse-1]`, a list of
comments. Sefaria records the license it negotiated for every version, so
this source chooses, per book, the largest English version whose license is
on the allow-list (Public Domain, CC0, CC BY, CC BY-SA), preferring the
titles listed in `prefer`; anything CC-BY-NC or all-rights-reserved is never
read. The build logs which version each book got and which books got none.

Numbering is the Masoretic Text's. When the WLC translation is in the same
build its ingest-time renumbering is reused verse for verse (psalm titles
included); otherwise the Hebrew rule table alone applies and the build says
so.

Config: repo, commit, path (the author's directory), prefer, reference.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import quote

from .. import db, fetch, htmltext, versification
from ..context import BuildContext
from ..model import Entry
from ..refs import BY_NAME, BY_OSIS, CANON, verse_id
from .base import Source

ALLOWED = {"PUBLICDOMAIN", "CC0", "CCBY", "CCBYSA"}
_TAG = re.compile(r"\[[a-z]{2,3}\]")  # "[pt]", "[de]": a foreign-language version misfiled
_HF = "https://huggingface.co"

# Sefaria's book titles that are not this app's names.
BOOKS = {
    "i samuel": "1Sam", "ii samuel": "2Sam", "i kings": "1Kgs", "ii kings": "2Kgs",
    "i chronicles": "1Chr", "ii chronicles": "2Chr",
}  # fmt: skip


def license_key(value: str | None) -> str:
    """'CC-BY 4.0' -> 'CCBY', 'CC0' -> 'CC0', 'Public Domain' -> 'PUBLICDOMAIN';
    NC stays NC. Version numbers (4.0, 3.0) are dropped, nothing else."""
    text = re.sub(r"\d\.\d", "", (value or "").upper())
    return re.sub(r"[^A-Z0-9]", "", text)


def book_id(title: str, author: str) -> int | None:
    """'Rashi on Genesis' -> 1; None for books outside the canon (or the author)."""
    name = title
    for prefix in (f"{author} on ", "on "):
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break
    key = name.strip().lower()
    osis = BOOKS.get(key)
    if osis:
        return BY_OSIS[osis].id
    book = BY_NAME.get(key)
    return book.id if book else None


@dataclass(frozen=True, slots=True)
class Version:
    path: str  # export-relative path of the json file
    title: str
    license: str
    size: int


def choose(versions: list[Version], prefer: list[str]) -> Version | None:
    """The allowed version highest in `prefer`, else the largest allowed one."""
    ok = [v for v in versions if license_key(v.license) in ALLOWED and not _TAG.search(v.path)]
    if not ok:
        return None

    def rank(v: Version) -> tuple[int, int]:
        pos = prefer.index(v.title) if v.title in prefer else len(prefer)
        return pos, -v.size

    return sorted(ok, key=rank)[0]


def clean(comment: str) -> str:
    return "\n".join(htmltext.blocks(comment, keep_bold=True)).strip()


def chapters(text, book_name: str) -> tuple[list, str]:
    """The chapter/verse array of a version's `text`, with a note on how it
    was found. Simple texts store a list; "complex" ones (a book with an
    introduction, like Ibn Ezra on Genesis) store a dict keyed by node title,
    the verse-by-verse commentary under "" (the default node) or the book's
    name, an introduction under its own title, which is not verse-anchored
    and is left out."""
    if isinstance(text, list):
        return text, "list"
    if isinstance(text, dict):
        for key in ("", "default", book_name):
            value = text.get(key)
            if isinstance(value, list):
                return value, f"node {key!r}"
        for key, value in text.items():
            if isinstance(value, list) and any(isinstance(x, list) for x in value):
                return value, f"node {key!r} (first verse-shaped node of {sorted(text)})"
        return [], f"no verse-shaped node among {sorted(text)}"
    return [], f"unexpected {type(text).__name__}"


def entries_for(book: int, text: list, source_id: str, resolve) -> Iterator[Entry]:
    """One entry per verse with comments. `resolve(book, chapter, verse)`
    returns the canonical verse id."""
    name = CANON[book - 1].name
    for c, chapter in enumerate(text, 1):
        if not isinstance(chapter, list):
            continue
        for v, comments in enumerate(chapter, 1):
            if isinstance(comments, str):
                comments = [comments]
            parts = [clean(x) for x in comments if isinstance(x, str) and x.strip()]
            parts = [p for p in parts if p]
            if not parts:
                continue
            vid = resolve(book, c, v)
            cc, cv = vid // 1000 % 1000, vid % 1000
            cite = f"{name} {cc}" if cv == 0 else f"{name} {cc}:{cv}"
            if (cc, cv) != (c, v):
                cite += f" (Hebrew {c}:{v})"
            yield Entry(source_id, vid, vid, "\n\n".join(parts), citation=cite)


class SefariaExportSource(Source):
    def build(self, ctx: BuildContext) -> None:
        db.add_source(ctx.conn, self.id, self.cfg, self.cfg.get("commit", "sample")[:12])
        author = self.cfg["author"]
        prefer = list(self.cfg.get("prefer", []))
        ref = self.cfg.get("reference", "web")
        resolve, how = self._resolver(ctx, ref)
        ctx.log(f"{self.id}: Masoretic numbering mapped {how}")

        total = 0
        chosen: list[str] = []
        none: list[str] = []
        for title, versions in self._books(ctx):
            book = book_id(title, author)
            if book is None:
                continue
            pick = choose(versions, prefer)
            if pick is None:
                none.append(f"{title} ({', '.join(sorted({v.license or '?' for v in versions}))})")
                continue
            data = json.loads(self._read(ctx, pick.path))
            text, how = chapters(data.get("text", []), CANON[book - 1].name)
            got = list(entries_for(book, text, self.id, resolve))
            total += db.add_entries(ctx.conn, got)
            note = "" if how == "list" else f" ({how})"
            chosen.append(f"{CANON[book - 1].osis}: {pick.title} [{pick.license}] {len(got)}{note}")
        ctx.conn.commit()
        ctx.log(f"{self.id}: {total} entries in {len(chosen)} books")
        for line in chosen:
            ctx.log(f"{self.id}:   {line}")
        if none:
            ctx.log(f"{self.id}: no English version with an allowed license: {none}")
        if self._by_rule:
            ctx.log(
                f"{self.id}: {len(self._by_rule)} references not in the WLC's numbering, placed "
                f"by the Hebrew rule table: {self._by_rule[:8]}"
            )

    # -- numbering ----------------------------------------------------------

    _by_rule: list[str] = []

    def _resolver(self, ctx: BuildContext, ref: str):
        """(resolve function, how it works). The WLC's ingest trace when the
        WLC is in this build, the rule table for anything it lacks."""
        trace = versification.translation_trace(ctx.conn, "wlc")
        self._by_rule = []

        def by_rules(book: int, c: int, v: int) -> int:
            b, ec, ev = versification.shift_mt(book, c, v)
            return verse_id(b, ec, ev)

        if not trace:
            return by_rules, "by the Hebrew rule table only: build with wlc for psalm titles"

        def by_wlc(book: int, c: int, v: int) -> int:
            vid = trace.get((book, c, v))
            if vid is None:
                self._by_rule.append(f"{CANON[book - 1].osis} {c}:{v}")
                return by_rules(book, c, v)
            return vid

        return by_wlc, "through the WLC's ingest (psalm titles included)"

    # -- files --------------------------------------------------------------

    def _books(self, ctx: BuildContext) -> Iterator[tuple[str, list[Version]]]:
        """(Sefaria title, English versions) for every book under `path`."""
        root = self.cfg["path"].rstrip("/")
        if ctx.sample:
            folder = ctx.fixtures / "commentaries" / self.id
            for english in sorted(folder.rglob("English")):
                versions = []
                for f in sorted(english.glob("*.json")):
                    meta = json.loads(f.read_text(encoding="utf-8"))
                    rel = f.relative_to(folder).as_posix()
                    versions.append(
                        Version(
                            rel,
                            meta.get("versionTitle", f.stem),
                            meta.get("license", ""),
                            f.stat().st_size,
                        )
                    )
                yield english.parent.name, versions
            return
        for category in self._dirs(root):
            for book_dir in self._dirs(category):
                title = book_dir.rsplit("/", 1)[-1]
                files = [e for e in self._list(f"{book_dir}/English") if e.get("type") == "file"]
                versions = []
                for e in files:
                    path = e["path"]
                    if not path.endswith(".json") or path.endswith("/merged.json"):
                        continue
                    head = json.loads(self._read(ctx, path))
                    if head.get("actualLanguage", head.get("language", "en")) != "en":
                        continue
                    versions.append(
                        Version(
                            path,
                            head.get("versionTitle", ""),
                            head.get("license", ""),
                            int(e.get("size", 0)),
                        )
                    )
                yield title, versions

    def _dirs(self, path: str) -> list[str]:
        return [e["path"] for e in self._list(path) if e.get("type") == "directory"]

    def _list(self, path: str) -> list[dict]:
        url = (
            f"{_HF}/api/models/{self.cfg['repo']}/tree/{self.cfg['commit']}/{quote(path, safe='/')}"
        )
        try:
            return json.loads(fetch.download(url).read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 - a missing book directory is normal
            if "404" in str(e):
                return []
            raise SystemExit(f"{self.id}: listing {url} failed: {e}") from e

    def _read(self, ctx: BuildContext, path: str) -> str:
        if ctx.sample:
            return (ctx.fixtures / "commentaries" / self.id / path).read_text(encoding="utf-8")
        url = f"{_HF}/{self.cfg['repo']}/resolve/{self.cfg['commit']}/{quote(path, safe='/')}"
        return fetch.download(url).read_text(encoding="utf-8")
