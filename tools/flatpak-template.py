#!/usr/bin/env python3
"""Render packaging/flatpak/flatpak-flutter.yml from its template.

    python tools/flatpak-template.py --commit <sha> --manifest-sha256 <hex>
    python tools/flatpak-template.py --tag v0.1.0 --manifest-sha256 <hex>

Fills the app source (a commit for a CI proof, a tag for a release), the
Flutter tag from .github/actions/setup-flutter/action.yml, and the content
database's version and checksum from app/content.lock. The content
release's manifest.json has no checksum in the lock, so the caller
supplies it (flatpak-sources.yml downloads the file and hashes it).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "packaging/flatpak/flatpak-flutter.template.yml"
OUT = ROOT / "packaging/flatpak/flatpak-flutter.yml"


def flutter_tag() -> str:
    text = (ROOT / ".github/actions/setup-flutter/action.yml").read_text()
    match = re.search(r"flutter-version:\s*['\"]?([0-9][0-9.]*)", text)
    if not match:
        sys.exit("setup-flutter/action.yml: no flutter-version pin found")
    return match.group(1)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    ref = parser.add_mutually_exclusive_group(required=True)
    ref.add_argument("--commit")
    ref.add_argument("--tag")
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args(argv)
    lock = json.loads((ROOT / "app/content.lock").read_text())
    if not re.fullmatch(r"[0-9a-f]{64}", lock.get("sha256", "")):
        sys.exit("app/content.lock has no sha256; publish a content release first")
    if not re.fullmatch(r"[0-9a-f]{64}", args.manifest_sha256):
        sys.exit("--manifest-sha256 must be 64 hex characters")
    app_ref = f"commit: {args.commit}" if args.commit else f"tag: {args.tag}"
    text = TEMPLATE.read_text()
    for key, value in {
        "@APP_REF@": app_ref,
        "@FLUTTER_TAG@": flutter_tag(),
        "@CONTENT_VERSION@": lock["version"],
        "@CONTENT_SHA256@": lock["sha256"],
        "@CONTENT_MANIFEST_SHA256@": args.manifest_sha256,
    }.items():
        assert key in text, key
        text = text.replace(key, value)
    OUT.write_text(text)
    print(f"{OUT.relative_to(ROOT)}: {app_ref}, Flutter {flutter_tag()}, content {lock['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
