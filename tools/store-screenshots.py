#!/usr/bin/env python3
"""Frames the checklist's screenshots for the store listings (docs/plan.md,
S4).

Input: a directory holding one `screenshots-<target>` directory per target
as `screenshots.yml` uploads them (`<target>/screenshots/<name>.png`), or
the site's `screenshots/<target>/screenshots/` layout; either is found.
Output: one directory per store surface, each screenshot on a canvas of a
size that store accepts, with a caption band above it (store/captions.json)
and the app's colours; plus Play's feature graphic. No alpha channel, as
the App Store requires.

    python3 tools/store-screenshots.py <root> <out>

Sizes (checked against the stores' current specifications, 2026-09-17):
Play phone 1080x1920 (any 16:9..9:16 between 320 and 3840 px), Play
feature graphic 1024x500; App Store iPhone 6.9" 1260x2736, iPad 13"
2048x2732, Mac 2560x1600; Microsoft Store 1920x1080. A missing target is
reported and skipped, so a partial run still writes what it can.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BROWN = (0x5B, 0x46, 0x36)
CREAM = (0xF4, 0xE7, 0xCE)
ROOT = Path(__file__).resolve().parent.parent

# surface: (source target, canvas width, canvas height)
SURFACES = {
    "play/phone": ("android", 1080, 1920),
    "play/tablet-10": ("ipad", 2048, 2732),
    "appstore/iphone-6.9": ("iphone", 1260, 2736),
    "appstore/ipad-13": ("ipad", 2048, 2732),
    "appstore/mac": ("macos", 2560, 1600),
    "msstore/desktop": ("windows", 1920, 1080),
}

# Not part of any store listing: the Support screen is hidden in store
# builds (SR_DISTRIBUTION), and the second launch looks like the first.
SKIP = {"03-support", "10-second-launch"}


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def find_shots(root: Path, target: str) -> list[Path]:
    for d in (root / f"screenshots-{target}", root / target, root / "screenshots" / target):
        shots = d / "screenshots"
        if shots.is_dir():
            return sorted(shots.glob("*.png"))
    return []


def fit(im: Image.Image, w: int, h: int) -> Image.Image:
    scale = min(w / im.width, h / im.height)
    return im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def frame(src: Path, caption: str, w: int, h: int) -> Image.Image:
    shot = Image.open(src).convert("RGB")
    canvas = Image.new("RGB", (w, h), CREAM)
    draw = ImageDraw.Draw(canvas)
    size = max(28, round(min(w, h) * 0.045))
    fnt = font(size)
    margin = round(w * 0.06)
    lines = wrap(draw, caption, fnt, w - 2 * margin)
    line_h = round(size * 1.3)
    band = margin + len(lines) * line_h + margin
    y = margin
    for line in lines:
        tw = draw.textlength(line, font=fnt)
        draw.text(((w - tw) / 2, y), line, font=fnt, fill=BROWN)
        y += line_h
    fitted = fit(shot, w - 2 * margin, h - band - margin)
    x = (w - fitted.width) // 2
    canvas.paste(fitted, (x, band))
    # A hairline around the screenshot so cream-on-cream edges read.
    draw.rectangle(
        (x - 1, band - 1, x + fitted.width, band + fitted.height),
        outline=BROWN,
        width=2,
    )
    return canvas


def feature_graphic(out: Path) -> None:
    w, h = 1024, 500
    canvas = Image.new("RGB", (w, h), CREAM)
    icon = Image.open(ROOT / "packaging/icon/org.sevenreadings.SevenReadings-512.png")
    icon = icon.convert("RGBA").resize((320, 320), Image.LANCZOS)
    canvas.paste(icon, (70, 90), icon)
    draw = ImageDraw.Draw(canvas)
    title, tf = "Seven Readings", font(64)
    draw.text((430, 140), title, font=tf, fill=BROWN)
    draw.text((432, 240), "Scripture, seven traditions,", font=font(34), fill=BROWN)
    draw.text((432, 290), "all on your device.", font=font(34), fill=BROWN)
    assert draw.textlength(title, font=tf) < w - 450, "title clipped"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, optimize=True)
    print(f"{out}: feature graphic")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    root, out = Path(argv[1]), Path(argv[2])
    captions = json.loads((ROOT / "store/captions.json").read_text())
    written = 0
    for surface, (target, w, h) in SURFACES.items():
        shots = [s for s in find_shots(root, target) if s.stem not in SKIP]
        if not shots:
            print(f"{surface}: no screenshots for {target} under {root}, skipped")
            continue
        dest = out / surface
        dest.mkdir(parents=True, exist_ok=True)
        for shot in shots:
            caption = captions.get(shot.stem)
            if caption is None:
                print(f"{surface}: {shot.name} has no caption in store/captions.json", file=sys.stderr)
                return 1
            frame(shot, caption, w, h).save(dest / shot.name, optimize=True)
            written += 1
        print(f"{surface}: {len(shots)} screenshots at {w}x{h} from {target}")
    feature_graphic(out / "play/feature-graphic.png")
    if written == 0:
        print("no screenshots framed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
