"""Fetch and verify pinned upstream files, with a local cache."""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from collections.abc import Iterator
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str) -> Path:
    """Download `url` into the cache (once) and return the cached file."""
    import httpx  # lazy: sample builds and tests need no network stack

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(url.encode()).hexdigest()[:16] + "_" + url.rsplit("/", 1)[-1]
    target = CACHE_DIR / name
    if not target.exists():
        with httpx.stream("GET", url, follow_redirects=True, timeout=120) as r:
            r.raise_for_status()
            tmp = target.with_suffix(target.suffix + ".part")
            with tmp.open("wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
            tmp.rename(target)
    return target


def fetch(url: str, expected_sha256: str | None) -> Path:
    """Download `url` into the cache (once) and verify its SHA-256.

    An expected value of "TODO" (or empty) downloads, prints the actual hash and
    refuses to continue, so nobody ships content from an unpinned upstream by
    accident. `srp lock --write <source>` records the hash.
    """
    target = download(url)
    actual = sha256_of(target)
    if not expected_sha256 or expected_sha256.upper().startswith("TODO"):
        raise SystemExit(
            f'\nUnpinned upstream: {url}\n  sha256 = "{actual}"\n'
            "Run `srp lock --write <source>` (or paste this into sources.toml) and re-run."
        )
    if actual != expected_sha256:
        raise SystemExit(
            f"Checksum mismatch for {url}\n  expected {expected_sha256}\n  got      {actual}"
        )
    return target


def zip_members(path: Path, suffix: str) -> Iterator[tuple[str, io.TextIOWrapper]]:
    with zipfile.ZipFile(path) as z:
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            if info.filename.lower().endswith(suffix) and not info.is_dir():
                with z.open(info) as raw:
                    yield info.filename, io.TextIOWrapper(raw, encoding="utf-8-sig")


def write_pin(toml_text: str, url: str, sha256: str) -> tuple[str, int]:
    """Set `sha256 = "..."` on every line that directly follows `url = "<url>"`
    in sources.toml text. Returns (new text, number of entries updated); the
    file's comments and layout are untouched. `urls = [...]` lists are not
    handled: paste those by hand."""
    lines = toml_text.split("\n")
    n = 0
    url_line = re.compile(r'^\s*url\s*=\s*"([^"]*)"\s*(#.*)?$')
    for i, line in enumerate(lines[:-1]):
        m = url_line.match(line)
        if m and m.group(1) == url and lines[i + 1].lstrip().startswith("sha256 ="):
            prefix, _, rest = lines[i + 1].partition("=")
            comment = ""
            if "#" in rest:
                rest, _, comment = rest.partition("#")
                comment = "   #" + comment
            lines[i + 1] = f'{prefix}= "{sha256}"{comment}'
            n += 1
    return "\n".join(lines), n
