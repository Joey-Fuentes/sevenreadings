"""Maps `kind` in sources.toml to a Source implementation."""

from __future__ import annotations

import tomllib
from pathlib import Path

from .sources.base import Source
from .sources.jsonl_commentary import JsonlCommentarySource
from .sources.stubs import (
    HaydockSource,
    HcfDatabaseSource,
    IccSource,
    SefariaExportSource,
    TafsirApiSource,
)
from .sources.usfm_bible import UsfmBibleSource

SOURCES_TOML = Path(__file__).resolve().parents[1] / "sources.toml"

KINDS: dict[str, type[Source]] = {
    "usfm_zip": UsfmBibleSource,
    "jsonl": JsonlCommentarySource,
    "sefaria_export": SefariaExportSource,
    "haydock": HaydockSource,
    "hcf_database": HcfDatabaseSource,
    "tafsir_api": TafsirApiSource,
    "icc": IccSource,
}

BIBLE_KINDS = {"usfm_zip"}

# Sample-mode sources: what CI builds from committed fixtures, no network.
SAMPLE_SOURCES: dict[str, dict] = {
    "web": {
        "kind": "usfm_zip", "name": "World English Bible", "abbreviation": "WEB",
        "language": "en", "license": "Public domain", "license_status": "clear",
        "url": "fixture",
    },
    "bsb": {
        "kind": "usfm_zip", "name": "Berean Standard Bible", "abbreviation": "BSB",
        "language": "en", "license": "Public domain (CC0)", "license_status": "clear",
        "url": "fixture",
    },
    "sample": {
        "kind": "jsonl", "perspective": "protestant", "author": "Fixture",
        "title": "Sample commentary (CI only)", "license": "CC0",
        "license_status": "clear", "url": "fixture",
    },
}


def load_config() -> dict[str, dict]:
    with SOURCES_TOML.open("rb") as f:
        return tomllib.load(f)


def make(source_id: str, cfg: dict) -> Source:
    try:
        cls = KINDS[cfg["kind"]]
    except KeyError as e:
        raise SystemExit(f"{source_id}: unknown kind {cfg.get('kind')!r}") from e
    return cls(source_id, cfg)
