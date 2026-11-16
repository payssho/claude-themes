"""Draw the neon night city as pixel art and package it for the plugin.

The city is drawn pixel by pixel on a small 480 x 300 canvas: isometric
blocks with 2:1 edges, one-pixel windows, one-pixel neon outlines. The
picture is then wrapped in a tiny SVG that the app scales up with crisp,
unsmoothed pixels, and written as hooks/scene.js. A 4x preview goes to
assets/night-city.png for the README.

    pip install pillow
    python night-theme/tools/build.py

Scale: the canvas fills a window about 1900 px wide, so one pixel of the
city is about 4 screen pixels, and about 10 canvas pixels make a centimetre.
Shops stand ~1.5 cm, small towers ~3 cm, the tallest ~9 cm.

The middle of the city stays low and dark, where the conversation sits; the
detail lives on the left and right edges, which stay visible.
"""

import base64
import io
import json
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SCENE_MODULE = ROOT / "hooks" / "scene.js"
PREVIEW = ROOT / "assets" / "night-city.png"

W, H = 480, 300  # the canvas: one pixel each
HX, HY = 8, 4  # half a tile on screen: tiles are 16 x 8, a 2:1 isometric grid
OX, OY = 240, -150  # screen position of grid (0, 0)
N = 100  # grid cells drawn along each axis (culled to the canvas)
PERIOD = 8  # 2 cells of road, then a 6 x 6 block of three 2 x 2 lots a side
COLOURS = 64  # palette of the final picture
MAX_SCENE = 131072  # the most characters the app takes for a scene

rnd = random.Random(7331)

# ---------- palette ----------

PAVEMENT = (27, 23, 53)
ROAD = (14, 12, 34)
LANE = (58, 50, 118)
TOWER = ((46, 41, 96), (31, 28, 68), (21, 19, 48))  # top, left, right
PLAIN = ((38, 34, 78), (27, 25, 58), (19, 17, 42))
DARK_WINDOW = (12, 10, 31)
WINDOWS = {
    "cyan": [(127, 246, 255), (200, 251, 255), (45, 226, 255)],
    "pink": [(255, 138, 216), (255, 62, 165), (201, 166, 255)],
    "warm": [(255, 216, 138), (255, 196, 107), (255, 241, 196)],
}
NEON = [(45, 226, 255), (255, 62, 165), (155, 107, 255), (255, 210, 63), (93, 255, 158), (255, 122, 61)]
FACADES = [(42, 31, 85), (29, 47, 85), (58, 31, 74), (27, 58, 70), (64, 34, 58)]
GLOWS = [(255, 210, 122), (127, 246, 255), (255, 138, 216), (185, 255, 122), (201, 166, 255)]
TREE = ((93, 255, 190), (47, 194, 142), (30, 130, 96))
TRAIN = ((238, 242, 255), (205, 214, 246), (150, 160, 200))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


# ---------- geometry ----------


def P(i, j, z=0):
    """Screen pixel of grid point (i, j) at height z."""
    return (round(OX + (i - j) * HX), round(OY + (i + j) * HY - z))


class Canvas:
    def __init__(self):
        self.img = Image.new("RGB", (W, H), PAVEMENT)
        self.d = ImageDraw.Draw(self.img)
        # Neon is drawn twice: on the picture, and on a glow layer blurred later.
        self.glow = Image.new("RGB", (W, H), (0, 0, 0))
        self.g = ImageDraw.Draw(self.glow)

    def px(self, x, y, c, glow=False):
        if 0 <= x < W and 0 <= y < H:
            self.img.putpixel((x, y), c)
            if glow:
                self.glow.putpixel((x, y), c)

    def poly(self, pts, c):
        self.d.polygon(pts, fill=c)

    def line(self, a, b, c, glow=False):
        self.d.line([a, b], fill=c)
        if glow:
            self.g.line([a, b], fill=c, width=2)

    def box(self, i, j, w, d, z0, z1, colours):
        """A block on the grid: left face (+j), right face (+i), then top.

        Returns the two visible faces as (x0, x1, top_y_at_x0, height, slope),
        so windows and signs can be laid on them pixel by pixel.
        """
        top, left, right = colours
        h = z1 - z0
        self.poly([P(i, j + d, z1), P(i + w, j + d, z1), P(i + w, j + d, z0), P(i, j + d, z0)], left)
        self.poly([P(i + w, j + d, z1), P(i + w, j, z1), P(i + w, j, z0), P(i + w, j + d, z0)], right)
        self.poly([P(i, j, z1), P(i + w, j, z1), P(i + w, j + d, z1), P(i, j + d, z1)], top)
        lx, ly = P(i, j + d, z1)
        fx, fy = P(i + w, j + d, z1)
        rx, _ = P(i + w, j, z1)
        return (lx, fx, ly, h, 0.5), (fx, rx, fy, h, -0.5)


def face_pixels(face, step_x=2, step_y=3, margin_top=3, margin_bottom=3):
    """Window positions on a face: every other column, following its slope."""
    x0, x1, y0, h, slope = face
    for x in range(x0 + 2, x1 - 1, step_x):
        top = y0 + int((x - x0) * slope)
        for y in range(top + margin_top, top + h - margin_bottom, step_y):
            yield x, y


# ---------- buildings ----------


def windows(cv, face, palette, p, dim=1.0, height=2):
    for x, y in face_pixels(face, step_y=height + 1):
        c = rnd.choice(WINDOWS[palette]) if rnd.random() < p else DARK_WINDOW
        c = shade(c, dim)
        for k in range(height):
            cv.px(x, y + k, c)


def roof_neon(cv, i, j, w, d, z, colour):
    a, b, c, e = P(i, j, z), P(i + w, j, z), P(i + w, j + d, z), P(i, j + d, z)
    for p, q in ((a, b), (b, c), (c, e), (e, a)):
        cv.line(p, q, colour, glow=True)
    fx, fy = c
    cv.line((fx, fy), (fx, fy + z), shade(colour, 0.85), glow=True)


def tower(cv, i0, j0, h, neon):
    a, w = 0.25, 1.5
    left, right = cv.box(i0 + a, j0 + a, w, w, 0, h, TOWER)
    palette = rnd.choice(list(WINDOWS))
    windows(cv, left, palette, 0.42)
    windows(cv, right, palette, 0.42, dim=0.7)
    if neon:
        roof_neon(cv, i0 + a, j0 + a, w, w, h, neon)
    # A rooftop box.
    cv.box(i0 + 0.6, j0 + 0.5, 0.5, 0.5, h, h + 2, ((60, 55, 120), (38, 34, 79), (28, 25, 60)))
    if h >= 40:
        x, y = P(i0 + 1.3, j0 + 1.2, h)
        cv.line((x, y), (x, y - 7), (106, 100, 168))
        cv.px(x, y - 8, (255, 59, 92), glow=True)
    if h >= 28 and rnd.random() < 0.3:
        # A billboard on the left face, near the top.
        x0, x1, y0, _, _ = left
        c = rnd.choice(NEON)
        for x in range(x0 + 2, x1 - 1):
            top = y0 + (x - x0) // 2 + 3
            for y in range(top, top + 4):
                cv.px(x, y, c, glow=True)


def plain_tower(cv, i0, j0, h):
    left, right = cv.box(i0 + 0.25, j0 + 0.25, 1.5, 1.5, 0, h, PLAIN)
    windows(cv, left, "warm", 0.18, dim=0.55)
    windows(cv, right, "cyan", 0.18, dim=0.45)


def storefront(cv, face, glow, awning, dim=1.0):
    x0, x1, y0, h, slope = face
    for x in range(x0 + 1, x1):
        top = y0 + int((x - x0) * slope)
        cv.px(x, top + h - 5, shade(awning, dim), glow=True)
        for y in range(top + h - 4, top + h - 1):
            c = glow if (x - x0) % 4 else shade(glow, 0.55)  # window frames
            cv.px(x, y, shade(c, dim))


def light_pool(cv, i, j, w, d, colour, strength=0.22):
    """Light spilling on the pavement, blended in."""
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(layer).polygon([P(i, j), P(i + w, j), P(i + w, j + d), P(i, j + d)], fill=colour)
    cv.img = Image.blend(cv.img, Image.composite(layer, cv.img, layer.convert("L").point(lambda v: 255 if v else 0)), strength)
    cv.d = ImageDraw.Draw(cv.img)


def shop(cv, i0, j0):
    facade, glow, neon = rnd.choice(FACADES), rnd.choice(GLOWS), rnd.choice(NEON)
    h = rnd.choice([9, 10, 12])
    light_pool(cv, i0 + 0.25, j0 + 1.75, 1.5, 0.6, glow)
    left, right = cv.box(i0 + 0.25, j0 + 0.25, 1.5, 1.5, 0, h, ((43, 39, 84), facade, shade(facade, 0.7)))
    storefront(cv, left, glow, neon)
    storefront(cv, right, glow, neon, dim=0.75)
    # A sign standing on the roof edge.
    x0, _, y0, _, _ = left
    for x in range(x0 + 3, x0 + 8):
        for y in range(y0 + (x - x0) // 2 - 4, y0 + (x - x0) // 2 - 1):
            cv.px(x, y, neon, glow=True)


def cafe(cv, i0, j0):
    neon = rnd.choice(NEON)
    warm = (255, 207, 122)
    light_pool(cv, i0 + 0.25, j0 + 1.6, 1.5, 0.9, warm, 0.26)
    left, right = cv.box(i0 + 0.25, j0 + 0.25, 1.5, 1.3, 0, 10, ((43, 39, 84), (59, 35, 64), (41, 24, 45)))
    storefront(cv, left, warm, neon)
    storefront(cv, right, warm, neon, dim=0.75)
    # Terrace: two tables with parasols.
    for ti in (0.6, 1.3):
        x, y = P(i0 + ti, j0 + 1.85)
        cv.px(x, y, (217, 212, 255))
        cv.px(x, y - 1, (207, 200, 255))
        cv.px(x, y - 2, (207, 200, 255))
        for dx in (-2, -1, 0, 1, 2):
            cv.px(x + dx, y - 3, neon)


def park(cv, i0, j0):
    cv.poly([P(i0 + 0.2, j0 + 0.2), P(i0 + 1.8, j0 + 0.2), P(i0 + 1.8, j0 + 1.8), P(i0 + 0.2, j0 + 1.8)], (16, 41, 46))
    for ti, tj in ((0.6, 0.6), (1.4, 0.55), (0.55, 1.4), (1.45, 1.45)):
        x, y = P(i0 + ti, j0 + tj)
        cv.px(x, y, (58, 42, 72))
        cv.px(x, y - 1, (58, 42, 72))
        cv.poly([(x - 2, y - 3), (x, y - 4), (x + 2, y - 3), (x, y - 2)], TREE[0])
        cv.poly([(x - 2, y - 3), (x, y - 2), (x, y), (x - 2, y - 1)], TREE[1])
        cv.poly([(x, y - 2), (x + 2, y - 3), (x + 2, y - 1), (x, y)], TREE[2])
    x, y = P(i0 + 1, j0 + 1)
    cv.px(x, y - 4, (255, 231, 168), glow=True)
    cv.line((x, y - 3), (x, y), (74, 68, 128))


def plaza(cv, i0, j0):
    cv.poly([P(i0 + 0.2, j0 + 0.2), P(i0 + 1.8, j0 + 0.2), P(i0 + 1.8, j0 + 1.8), P(i0 + 0.2, j0 + 1.8)], (40, 35, 79))
    cv.box(i0 + 0.7, j0 + 0.7, 0.6, 0.6, 0, 2, ((74, 68, 144), (51, 46, 102), (40, 36, 80)))
    cv.poly([P(i0 + 0.8, j0 + 0.8, 2), P(i0 + 1.2, j0 + 0.8, 2), P(i0 + 1.2, j0 + 1.2, 2), P(i0 + 0.8, j0 + 1.2, 2)], NEON[0])
    x, y = P(i0 + 1, j0 + 1, 2)
    cv.g.ellipse([x - 4, y - 2, x + 4, y + 2], fill=NEON[0])


# ---------- metro ----------


def metro(cv, J, i_from, i_to, train_at):
    """An elevated line along the i road at J, with one train parked on it."""
    z = 18
    for i in range(i_from - i_from % PERIOD + 1, i_to, PERIOD):
        x, y = P(i, J + 1)
        cv.line((x, y), (x, y - z), (31, 27, 68))
    cv.box(i_from, J + 0.8, i_to - i_from, 0.4, z - 2, z, ((58, 53, 120), (33, 29, 72), (25, 22, 56)))
    a, b = P(i_from, J + 1.2, z - 2), P(i_to, J + 1.2, z - 2)
    cv.line(a, b, NEON[0], glow=True)
    for k in range(4):
        i = train_at + k * 1.1
        left, right = cv.box(i, J + 0.8, 1.0, 0.4, z, z + 3, TRAIN)
        x0, x1, y0, _, _ = left
        for x in range(x0, x1):
            cv.px(x, y0 + (x - x0) // 2 + 1, NEON[0], glow=True)


# ---------- city ----------


def screen_range(fixed):
    """Grid span of an i road (j = fixed) that falls on the canvas."""
    ts = [t for t in range(-10, N + 10) if -40 < P(t, fixed)[0] < W + 40 and -40 < P(t, fixed)[1] < H + 60]
    return (ts[0] - 2, ts[-1] + 2) if ts else None


def road_through(x, y):
    """The i road whose line runs nearest screen point (x, y)."""
    j1 = ((y - OY) / HY - (x - OX) / HX) / 2
    return round((j1 - 1) / PERIOD) * PERIOD


def build():
    cv = Canvas()

    # Roads, with dotted lane lines.
    for r in range(0, N, PERIOD):
        cv.poly([P(-10, r), P(N + 10, r), P(N + 10, r + 2), P(-10, r + 2)], ROAD)
        cv.poly([P(r, -10), P(r + 2, -10), P(r + 2, N + 10), P(r, N + 10)], ROAD)
    for r in range(0, N, PERIOD):
        for t in range(-10, N + 10):
            for x, y in (P(t + 0.5, r + 1), P(r + 1, t + 0.5)):
                if (x // 2) % 3 == 0:
                    cv.px(x, y, LANE)

    # Coloured light pools at crossings on the edges.
    for a in range(0, N, PERIOD):
        for b in range(0, N, PERIOD):
            x, y = P(a + 1, b + 1)
            if 0 <= x < W and 0 <= y < H and abs(x - OX) > 120 and rnd.random() < 0.5:
                cv.g.ellipse([x - 9, y - 4, x + 9, y + 4], fill=shade(rnd.choice(NEON), 0.7))

    left_line = road_through(60, 200)
    right_line = road_through(420, 110)
    lines = {}
    for J, at in ((left_line, 0.5), (right_line, 0.6)):
        span = screen_range(J + 1)
        if span:
            lines[J] = (span[0], span[1], round(span[0] + (span[1] - span[0]) * at))

    # Lots, row by row along j: a valid back-to-front order for grid blocks.
    for j0 in range(0, N, 2):
        if j0 % PERIOD == 0:
            continue
        if j0 % PERIOD == 2 and (j0 - 2) in lines:
            metro(cv, j0 - 2, *lines[j0 - 2])
        for i0 in range(0, N, 2):
            if i0 % PERIOD == 0:
                continue
            x, y = P(i0 + 1, j0 + 1)
            if not (-20 < x < W + 20 and -10 < y < H + 90):
                continue
            side = min(1.0, max(0.0, (abs(x - OX) - 105) / 30))
            r = rnd.random()
            if side < 0.5:
                # The covered middle: sparse, low, still.
                if r < 0.8:
                    continue
                plain_tower(cv, i0, j0, rnd.choice([10, 14]))
            elif r < 0.34:
                (cafe if rnd.random() < 0.3 else shop)(cv, i0, j0)
            elif r < 0.5:
                park(cv, i0, j0)
            elif r < 0.58:
                plaza(cv, i0, j0)
            elif r < 0.68:
                continue
            else:
                h = rnd.choice([16, 20, 28, 28, 40, 52, 64])
                tower(cv, i0, j0, h, rnd.choice(NEON) if rnd.random() < 0.45 else None)

    # Neon glow: the glow layer, blurred, added on top.
    glow = cv.glow.filter(ImageFilter.GaussianBlur(2.2))
    img = Image.blend(cv.img, ImageChops.add(cv.img, glow), 0.55)

    # Atmosphere: a magenta haze low left, cyan high right, darker sky at the top.
    img = atmosphere(img)
    return img.quantize(colors=COLOURS, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)


def atmosphere(img):
    over = Image.new("RGB", (W, H), (0, 0, 0))
    od = ImageDraw.Draw(over)
    od.ellipse([-120, 150, 180, 420], fill=(120, 20, 80))
    od.ellipse([300, -120, 620, 160], fill=(10, 90, 120))
    over = over.filter(ImageFilter.GaussianBlur(40))
    img = ImageChops.add(img, Image.blend(Image.new("RGB", (W, H)), over, 0.35))
    top = Image.new("L", (W, H), 0)
    td = ImageDraw.Draw(top)
    for y in range(70):
        td.line([(0, y), (W, y)], fill=int(200 * (1 - y / 70) ** 1.6))
    return Image.composite(Image.new("RGB", (W, H), (10, 8, 32)), img, top)


def main():
    img = build()

    # The scene: the picture inside an SVG that scales it with crisp pixels.
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">'
        f'<image width="{W}" height="{H}" style="image-rendering:pixelated" image-rendering="optimizeSpeed" '
        f'href="data:image/png;base64,{data}"/></svg>'
    )
    if len(svg) > MAX_SCENE:
        raise SystemExit(f"The scene is {len(svg)} characters; the app takes at most {MAX_SCENE}.")
    SCENE_MODULE.write_text(
        "// Generated by tools/build.py: edit that, then run\n"
        "//   python night-theme/tools/build.py\n"
        f"export const SCENE = {json.dumps(svg)}\n",
        encoding="utf-8",
    )

    # The preview: 4x, plain RGB.
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").resize((W * 4, H * 4), Image.Resampling.NEAREST).save(PREVIEW, optimize=True)

    print(f"{SCENE_MODULE.relative_to(ROOT)}: {len(svg)} characters")
    print(f"{PREVIEW.relative_to(ROOT)}: {W * 4} x {H * 4}")


if __name__ == "__main__":
    main()
