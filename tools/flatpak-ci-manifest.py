#!/usr/bin/env python3
"""The Flatpak manifest as CI builds it: the bundle just built, not a release.

    python tools/flatpak-ci-manifest.py packaging/flatpak/<id>.yml <bundle-dir> > <out>.yml

Copies the submission manifest, replaces the app module's archive source
(the release tarball) with a `dir` source at <bundle-dir>, and makes every
`file` source's path absolute so the copy can live anywhere. Everything
else (runtime, permissions, build commands, the desktop file, metainfo,
icons) is exactly what Flathub would build, which is the point.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    manifest = Path(argv[0]).resolve()
    bundle = Path(argv[1]).resolve()
    if not (bundle / "sevenreadings").exists():
        print(f"{bundle}: no sevenreadings binary; build the Linux app first", file=sys.stderr)
        return 1
    data = yaml.safe_load(manifest.read_text())
    (module,) = [m for m in data["modules"] if m["name"] == "sevenreadings"]
    sources = []
    for source in module["sources"]:
        if source["type"] == "archive":
            sources.append({"type": "dir", "path": str(bundle), "dest": source.get("dest", ".")})
        elif source["type"] == "file" and "path" in source:
            sources.append({**source, "path": str((manifest.parent / source["path"]).resolve())})
        else:
            sources.append(source)
    module["sources"] = sources
    sys.stdout.write(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
