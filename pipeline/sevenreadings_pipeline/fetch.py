"""Fetch and verify pinned upstream files, with a local cache."""

from __future__ import annotations

import hashlib
import io
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


def fetch(url: str, expected_sha256: str | None) -> Path:
    """Download `url` into the cache (once) and verify its SHA-256.

    An expected value of "TODO" (or empty) downloads, prints the actual hash and
    refuses to continue, so nobody ships content from an unpinned upstream by
    accident.
    """
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
    actual = sha256_of(target)
    if not expected_sha256 or expected_sha256.upper().startswith("TODO"):
        raise SystemExit(
            f'\nUnpinned upstream: {url}\n  sha256 = "{actual}"\n'
            "Paste this into sources.toml and re-run."
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
