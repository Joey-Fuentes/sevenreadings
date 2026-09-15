#!/usr/bin/env python3
"""The contact sheet of the checklist's screenshots, one page per site build.

    python tools/screenshots-page.py <site>/screenshots [run-id]

Expects <target>/screenshots/*.png and <target>/build/integration_response_data.json
as tools/site-screenshots.sh lays them out; writes index.html beside them.
"""

from __future__ import annotations

import html
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def main(argv: list[str]) -> int:
    root = Path(argv[0])
    run = argv[1] if len(argv) > 1 else ""
    sections = []
    for target in sorted(p for p in root.iterdir() if p.is_dir()):
        shots = sorted((target / "screenshots").glob("*.png"))
        report_path = target / "build" / "integration_response_data.json"
        report = json.loads(report_path.read_text()) if report_path.exists() else {}
        facts = ", ".join(f"{k} {v}" for k, v in report.items() if k != "screenshots")
        figures = "\n".join(
            f'<figure><a href="{target.name}/screenshots/{s.name}">'
            f'<img loading="lazy" src="{target.name}/screenshots/{s.name}" alt="{s.stem}"></a>'
            f"<figcaption>{html.escape(s.stem)}</figcaption></figure>"
            for s in shots
        )
        sections.append(
            f"<section><h2>{html.escape(target.name)}</h2>"
            f"<p>{html.escape(facts)}</p><div class=grid>{figures}</div></section>"
        )
    built = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    style = """
body { font: 15px/1.5 system-ui, sans-serif; color: #2b211b; background: #FFF8F5;
       margin: 0 auto; padding: 24px; max-width: 1400px; }
h1, h2 { color: #5B4636; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
figure { margin: 0; }
img { width: 100%; height: auto; border: 1px solid #d9cfc6; border-radius: 8px; background: #fff; }
figcaption { font-size: 13px; color: #6b5b50; }
"""
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Seven Readings: screenshots</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{style}</style></head><body>
<h1>Seven Readings: the first-launch checklist, every target</h1>
<p>Taken by the app's own integration test on each target (docs/plan.md,
section 2), from screenshots.yml run {html.escape(run)}; page built {built}.
Sample content unless the run says otherwise.</p>
{"".join(sections)}
</body></html>
"""
    (root / "index.html").write_text(page, encoding="utf-8")
    print(f"screenshots/index.html: {len(sections)} targets")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
