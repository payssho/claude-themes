"""Render the neon city to the pixel-art picture the theme shows.

The city is drawn as an SVG by scene.js (Node), screenshotted at a small size
by a headless Chromium browser (Edge or Chrome), then turned into pixel art:
colours reduced to a small palette, no dithering, and every pixel scaled up
as a crisp block. The result is a still PNG, so the app has nothing to
animate or redraw: no cost to performance.

    python night-theme/tools/render.py

Needs Node, Pillow (pip install pillow) and Edge or Chrome. Writes
assets/night-city.png (at most 1 MiB and 4096 px a side, the app's limits).
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "night-city.png"

SMALL = (1280, 800)  # the size the city is drawn at: one pixel of pixel art each
SCALE = 2  # each pixel becomes a SCALE x SCALE block: 2560 x 1600
COLOURS = 128  # palette size of the final picture

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
]


def browser() -> str:
    for candidate in BROWSERS:
        if os.path.isfile(candidate) or shutil.which(candidate):
            return candidate
    sys.exit("No Edge or Chrome found: add its path to BROWSERS in render.py.")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        svg = tmp / "scene.svg"
        shot = tmp / "shot.png"

        # 1. The SVG, frozen: every light held at its own moment, crisp edges.
        subprocess.run(["node", str(ROOT / "tools" / "export-svg.mjs"), str(svg)], check=True)

        # 2. A screenshot at the small size.
        subprocess.run(
            [
                browser(),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--window-size={SMALL[0]},{SMALL[1]}",
                f"--user-data-dir={tmp / 'profile'}",
                f"--screenshot={shot}",
                svg.as_uri(),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 3. Pixel art: a small palette with no dithering, then crisp blocks.
        small = Image.open(shot).convert("RGB").crop((0, 0, *SMALL))
        small = small.quantize(colors=COLOURS, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
        # Saved as plain RGB: the app does not draw palette (indexed) PNGs.
        big = small.resize((SMALL[0] * SCALE, SMALL[1] * SCALE), Image.Resampling.NEAREST).convert("RGB")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        big.save(OUT, optimize=True)

    size = OUT.stat().st_size
    print(f"{OUT.relative_to(ROOT)}: {big.width} x {big.height}, {size / 1024:.0f} KiB")
    if size > 1024 * 1024:
        sys.exit("Over the app's 1 MiB limit: lower COLOURS or SMALL.")


if __name__ == "__main__":
    main()
