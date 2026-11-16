"""Draw the neon night city as pixel art and package it for the plugin.

The city is written straight as an SVG on a 480 x 300 pixel grid, one unit
per pixel: isometric blocks with window patterns laid on their faces, neon
outlines with a soft glow. A mosaic filter then samples the whole picture
once per unit, so everything comes out as crisp square pixels, with 2:1
stair-stepped edges, when the app scales it up.

Each kind of building is drawn once, as a model, and placed with <use>, so
the whole city fits under the 131,072 characters the app takes for a scene
(it strips embedded bitmaps). The app draws the scene as a plain picture:
nothing runs once it is shown.

    python night-theme/tools/build.py

writes hooks/scene.js (the scene the plugin shows) and, when Edge or Chrome
is found, assets/night-city.png (a preview for the README).

Scale: the grid fills a window about 1900 px wide, so one pixel of the city
is about 4 screen pixels, and about 10 grid pixels make a centimetre. Shops
stand ~1.5 cm, small towers ~3 cm, the tallest ~9 cm. The middle stays low
and dark, where the conversation sits; the detail lives on the left and
right edges, which stay visible.
"""

import json
import os
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENE_MODULE = ROOT / "hooks" / "scene.js"
PREVIEW = ROOT / "assets" / "night-city.png"

W, H = 480, 300  # the pixel grid
HX, HY = 8, 4  # half a tile: tiles are 16 x 8, a 2:1 isometric grid
OX, OY = 240, -150  # pixel of grid (0, 0)
N = 100  # grid cells considered along each axis (culled to the picture)
PERIOD = 8  # 2 cells of road, then a 6 x 6 block of three 2 x 2 lots a side
MAX_SCENE = 131072

rnd = random.Random(7331)

# ---------- palette ----------

PAVEMENT = "#1b1735"
ROAD = "#0e0c22"
LANE = "#3a3276"
TOWER = ("#2e2960", "#1f1c44", "#1f1c44")  # top, left, right (the right is shaded)
PLAIN = ("#26224e", "#1b193a", "#1b193a")
ROOF_BOX = ("#3c3778", "#26224f", "#26224f")
DARK_WINDOW = "#0c0a1f"
WINDOWS = {
    "c": ["#7ff6ff", "#c8fbff", "#2de2ff"],
    "p": ["#ff8ad8", "#ff3ea5", "#c9a6ff"],
    "w": ["#ffd88a", "#ffc46b", "#fff1c4"],
}
NEON = ["#2de2ff", "#ff3ea5", "#9b6bff", "#ffd23f", "#5dff9e", "#ff7a3d"]
FACADES = ["#2a1f55", "#1d2f55", "#3a1f4a", "#1b3a46", "#40223a"]
GLOWS = ["#ffd27a", "#7ff6ff", "#ff8ad8", "#b9ff7a", "#c9a6ff"]
TREE = ("#5dffbe", "#2fc28e", "#1e8260")
TRAIN = ("#eef2ff", "#cdd6f6", "#cdd6f6")

TOWER_HEIGHTS = [16, 20, 28, 40, 52, 64]
PLAIN_HEIGHTS = [10, 14]
SHOP_HEIGHTS = [9, 10, 12]

# ---------- geometry ----------


def Q(i, j, z=0):
    """Pixel of grid point (i, j) at height z, relative to grid (0, 0)."""
    return (round((i - j) * HX), round((i + j) * HY - z))


def at(i, j):
    """Where a model drawn at grid (0, 0) goes for a lot at (i, j)."""
    return OX + (i - j) * HX, OY + (i + j) * HY


def pts(points):
    return " ".join(f"{x} {y}" for x, y in points)


def poly(points, fill):
    return f'<path style="fill:{fill}" d="M{pts(points)}z"/>'


def line(a, b, stroke, extra=""):
    return f'<path style="stroke:{stroke}"{extra} d="M{a[0]} {a[1]} {b[0]} {b[1]}"/>'


def box(i, j, w, d, z0, z1, colours, left_in="", right_in="", shade=0.38):
    """A block: left face (+j), right face (+i), then the top.

    left_in and right_in are drawn in each face's own flat coordinates
    (x along the face from its left end, y down from its top edge).
    """
    top, left, right = colours
    h = z1 - z0
    lx, ly = Q(i, j + d, z1)
    fx, fy = Q(i + w, j + d, z1)
    lw, rw = round(w * HX), round(d * HX)
    return (
        f'<g transform="matrix(1 .5 0 1 {lx} {ly})"><rect width="{lw}" height="{h}" style="fill:{left}"/>{left_in}</g>'
        f'<g transform="matrix(1 -.5 0 1 {fx} {fy})"><rect width="{rw}" height="{h}" style="fill:{right}"/>{right_in}'
        f'<rect width="{rw}" height="{h}" fill="#000" opacity="{shade}"/></g>'
        + poly([Q(i, j, z1), Q(i + w, j, z1), Q(i + w, j + d, z1), Q(i, j + d, z1)], top)
    )


# ---------- models ----------


def window_pattern(pid, palette, p):
    """A 3 x 3 tile of one-pixel windows, 1 x 2 each, some lit, some dark."""
    s = f'<pattern id="{pid}" width="6" height="9" patternUnits="userSpaceOnUse">'
    for r in range(3):
        for c in range(3):
            fill = rnd.choice(WINDOWS[palette]) if rnd.random() < p else DARK_WINDOW
            s += f'<rect x="{c * 2}" y="{r * 3}" width="1" height="2" fill="{fill}"/>'
    return s + "</pattern>"


def tower_model(h, palette):
    a, w = 0.25, 1.5
    win = lambda fw, fh: f'<rect x="2" y="3" width="{fw - 4}" height="{fh - 6}" fill="url(#w{palette})"/>'
    s = box(a, a, w, w, 0, h, TOWER, win(12, h), win(12, h))
    s += box(0.6, 0.5, 0.5, 0.5, h, h + 2, ROOF_BOX)
    if h >= 40:
        x, y = Q(1.3, 1.2, h)
        s += line((x, y), (x, y - 7), "#6a64a8")
        s += f'<rect x="{x}" y="{y - 8}" width="1" height="1" fill="#ff3b5c"/>'
    return f'<g id="t{h}{palette}">{s}</g>'


def neon_model(h):
    """A tower's neon roof outline and front edge, in its instance's --n."""
    a, w = 0.25, 1.5
    c = [Q(a, a, h), Q(a + w, a, h), Q(a + w, a + w, h), Q(a, a + w, h)]
    f = c[2]
    return f'<path id="n{h}" style="stroke:var(--n)" d="M{pts(c)}zM{f[0]} {f[1]}v{h}"/>'


def board_model(h):
    """A billboard high on a tower's left face, in its instance's --n."""
    lx, ly = Q(0.25, 1.75, h)
    return f'<g id="b{h}" transform="matrix(1 .5 0 1 {lx} {ly})"><rect x="1" y="3" width="10" height="4" style="fill:var(--n)"/></g>'


def plain_model(h):
    win = lambda fw, fh: f'<rect x="2" y="3" width="{fw - 4}" height="{fh - 6}" fill="url(#wd)" opacity=".5"/>'
    return f'<g id="q{h}">{box(0.25, 0.25, 1.5, 1.5, 0, h, PLAIN, win(12, h), win(12, h))}</g>'


def storefront(fw, fh):
    return (
        f'<rect x="1" y="{fh - 4}" width="{fw - 2}" height="3" style="fill:var(--g)"/>'
        f'<rect y="{fh - 5}" width="{fw}" height="1" style="fill:var(--n)"/>'
    )


def shop_model(h):
    pool = poly([Q(0.25, 1.75), Q(1.75, 1.75), Q(1.75, 2.35), Q(0.25, 2.35)], "var(--g)").replace("/>", ' fill-opacity=".22"/>')
    sign = '<rect x="2" y="-4" width="5" height="3" style="fill:var(--n)"/>'
    body = box(0.25, 0.25, 1.5, 1.5, 0, h, ("#2b2754", "var(--f)", "var(--f)"), storefront(12, h) + sign, storefront(12, h))
    return f'<g id="s{h}">{pool}{body}</g>'


def shop_glow_model(h):
    """What glows of a shop: its sign and awning."""
    lx, ly = Q(0.25, 1.75, h)
    return f'<g id="g{h}" transform="matrix(1 .5 0 1 {lx} {ly})"><rect x="2" y="-4" width="5" height="3" style="fill:var(--n)"/><rect y="{h - 5}" width="12" height="1" style="fill:var(--n)"/></g>'


def cafe_model():
    warm = "#ffcf7a"
    pool = poly([Q(0.25, 1.55), Q(1.75, 1.55), Q(1.75, 2.45), Q(0.25, 2.45)], warm).replace("/>", ' fill-opacity=".26"/>')
    front = lambda fw, fh: (
        f'<rect x="1" y="{fh - 4}" width="{fw - 2}" height="3" fill="{warm}"/>'
        f'<rect y="{fh - 5}" width="{fw}" height="1" style="fill:var(--n)"/>'
    )
    s = pool + box(0.25, 0.25, 1.5, 1.3, 0, 10, ("#2b2754", "#3b2340", "#3b2340"), front(12, 10), front(10, 10))
    for ti in (0.6, 1.3):  # the terrace: two tables under parasols
        x, y = Q(ti, 1.85)
        s += line((x, y), (x, y - 2), "#cfc8ff") + line((x - 2, y - 3), (x + 2, y - 3), "var(--n)")
    return f'<g id="cafe">{s}</g>'


def park_model():
    s = poly([Q(0.2, 0.2), Q(1.8, 0.2), Q(1.8, 1.8), Q(0.2, 1.8)], "#10292e")
    for ti, tj in ((0.6, 0.6), (1.4, 0.55), (0.55, 1.4), (1.45, 1.45)):
        x, y = Q(ti, tj)
        s += line((x, y), (x, y - 1), "#3a2a48")
        s += poly([(x - 2, y - 3), (x, y - 4), (x + 2, y - 3), (x, y - 2)], TREE[0])
        s += poly([(x - 2, y - 3), (x, y - 2), (x, y), (x - 2, y - 1)], TREE[1])
        s += poly([(x, y - 2), (x + 2, y - 3), (x + 2, y - 1), (x, y)], TREE[2])
    x, y = Q(1, 1)
    s += line((x, y - 3), (x, y), "#4a4480") + f'<rect x="{x}" y="{y - 4}" width="1" height="1" fill="#ffe7a8"/>'
    return f'<g id="park">{s}</g>'


def plaza_model():
    s = poly([Q(0.2, 0.2), Q(1.8, 0.2), Q(1.8, 1.8), Q(0.2, 1.8)], "#28234f")
    s += box(0.7, 0.7, 0.6, 0.6, 0, 2, ("#4a4490", "#332e66", "#332e66"))
    s += poly([Q(0.8, 0.8, 2), Q(1.2, 0.8, 2), Q(1.2, 1.2, 2), Q(0.8, 1.2, 2)], NEON[0])
    return f'<g id="plaza">{s}</g>'


def models():
    s = window_pattern("wc", "c", 0.45) + window_pattern("wp", "p", 0.42) + window_pattern("ww", "w", 0.45)
    s += window_pattern("wd", "w", 0.3)
    for h in TOWER_HEIGHTS:
        s += "".join(tower_model(h, p) for p in WINDOWS) + neon_model(h) + board_model(h)
    s += "".join(plain_model(h) for h in PLAIN_HEIGHTS)
    s += "".join(shop_model(h) + shop_glow_model(h) for h in SHOP_HEIGHTS)
    return s + cafe_model() + park_model() + plaza_model()


# ---------- metro ----------


def metro(J, i_from, i_to, train_at):
    """An elevated line along the i road at J, with one train stopped on it."""
    z = 18
    pillars = "".join(f"M{x} {y}v-{z}" for x, y in (Q(i, J + 1) for i in range(i_from - i_from % PERIOD + 1, i_to, PERIOD)))
    s = f'<path style="stroke:#1f1b44" d="{pillars}"/>'
    s += box(i_from, J + 0.8, i_to - i_from, 0.4, z - 2, z, ("#3a3578", "#211d48", "#211d48"))
    rail = line(Q(i_from, J + 1.2, z - 2), Q(i_to, J + 1.2, z - 2), NEON[0])
    train = ""
    for k in range(4):
        stripe = lambda fw, fh: f'<rect y="1" width="{fw}" height="1" fill="{NEON[0]}"/>'
        train += box(train_at + k * 1.1, J + 0.8, 1.0, 0.4, z, z + 3, TRAIN, stripe(8, 3), "", 0.3)
    out = f'<g transform="translate({OX} {OY})">{s}{rail}{train}</g>'
    glow = f'<g transform="translate({OX} {OY})">{rail}</g>'
    return out, glow


# ---------- city ----------


def screen_range(fixed):
    """Grid span of an i road (j = fixed) that falls on the picture."""
    ts = [t for t in range(-10, N + 10) if -40 < at(t, fixed)[0] < W + 40 and -40 < at(t, fixed)[1] < H + 60]
    return (ts[0] - 2, ts[-1] + 2) if ts else None


def road_through(x, y):
    """The i road whose line runs nearest pixel (x, y)."""
    j1 = ((y - OY) / HY - (x - OX) / HX) / 2
    return round((j1 - 1) / PERIOD) * PERIOD


def use(href, i, j, cls=""):
    x, y = at(i, j)
    return f'<use href="#{href}" x="{x}" y="{y}"{f" class={chr(34)}{cls}{chr(34)}" if cls else ""}/>'


def city():
    out, glow = [], []

    # Roads, with dashed lane lines.
    roads, lanes = [], []
    for r in range(0, N, PERIOD):
        roads.append(f"M{pts([Q(-10, r), Q(N + 10, r), Q(N + 10, r + 2), Q(-10, r + 2)])}z")
        roads.append(f"M{pts([Q(r, -10), Q(r + 2, -10), Q(r + 2, N + 10), Q(r, N + 10)])}z")
        lanes.append(f"M{pts([Q(-10, r + 1), Q(N + 10, r + 1)])}M{pts([Q(r + 1, -10), Q(r + 1, N + 10)])}")
    out.append(
        f'<g transform="translate({OX} {OY})"><path style="fill:{ROAD}" d="{"".join(roads)}"/>'
        f'<path style="stroke:{LANE}" stroke-dasharray="2 4" d="{"".join(lanes)}"/></g>'
    )

    # Coloured light pools at crossings on the edges.
    for a in range(0, N, PERIOD):
        for b in range(0, N, PERIOD):
            x, y = at(a + 1, b + 1)
            if 0 <= x < W and 0 <= y < H and abs(x - OX) > 120 and rnd.random() < 0.5:
                glow.append(f'<ellipse cx="{x}" cy="{y}" rx="9" ry="4" fill="{rnd.choice(NEON)}" opacity=".7"/>')

    lines = {}
    for J, frac in ((road_through(60, 200), 0.5), (road_through(420, 110), 0.6)):
        span = screen_range(J + 1)
        if span:
            lines[J] = (span[0], span[1], round(span[0] + (span[1] - span[0]) * frac))

    # Lots, row by row along j: a valid back-to-front order for grid blocks.
    for j0 in range(0, N, 2):
        if j0 % PERIOD == 0:
            continue
        if j0 % PERIOD == 2 and (j0 - 2) in lines:
            o, g = metro(j0 - 2, *lines[j0 - 2])
            out.append(o)
            glow.append(g)
        for i0 in range(0, N, 2):
            if i0 % PERIOD == 0:
                continue
            x, y = at(i0 + 1, j0 + 1)
            if not (-20 < x < W + 20 and -10 < y < H + 90):
                continue
            side = min(1.0, max(0.0, (abs(x - OX) - 105) / 30))
            r = rnd.random()
            if side < 0.5:
                # The covered middle: sparse, low, still.
                if r < 0.8:
                    continue
                out.append(use(f"q{rnd.choice(PLAIN_HEIGHTS)}", i0, j0))
            elif r < 0.34:
                if rnd.random() < 0.3:
                    out.append(use("cafe", i0, j0, f"n{rnd.randrange(len(NEON))}"))
                else:
                    h = rnd.choice(SHOP_HEIGHTS)
                    k = f"k{rnd.randrange(len(FACADES))}"
                    out.append(use(f"s{h}", i0, j0, k))
                    glow.append(use(f"g{h}", i0, j0, k))
            elif r < 0.5:
                out.append(use("park", i0, j0))
            elif r < 0.58:
                out.append(use("plaza", i0, j0))
                x, y = at(i0 + 1, j0 + 1)
                glow.append(f'<ellipse cx="{x}" cy="{y - 2}" rx="4" ry="2" fill="{NEON[0]}"/>')
            elif r < 0.68:
                continue
            else:
                h = rnd.choice([16, 20, 28, 28, 40, 52, 64])
                out.append(use(f"t{h}{rnd.choice(list(WINDOWS))}", i0, j0))
                n = f"n{rnd.randrange(len(NEON))}"
                if rnd.random() < 0.45:
                    out.append(use(f"n{h}", i0, j0, n))
                    glow.append(use(f"n{h}", i0, j0, n))
                if h >= 28 and rnd.random() < 0.3:
                    out.append(use(f"b{h}", i0, j0, n))
                    glow.append(use(f"b{h}", i0, j0, n))
    return out, glow


def svg():
    out, glow = city()
    colours = "".join(f".n{k}{{--n:{c}}}" for k, c in enumerate(NEON))
    colours += "".join(
        f".k{k}{{--f:{FACADES[k]};--g:{GLOWS[k]};--n:{NEON[(k + 1) % len(NEON)]}}}" for k in range(len(FACADES))
    )
    style = "path{fill:none;stroke-width:1}" + colours
    defs = (
        # Mosaic: keep the centre of every unit square, then grow it back to fill the square.
        f'<filter id="px" filterUnits="userSpaceOnUse" primitiveUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        '<feFlood x=".25" y=".25" width=".5" height=".5"/>'
        '<feComposite width="1" height="1"/>'
        '<feTile result="g"/>'
        '<feComposite in="SourceGraphic" in2="g" operator="in"/>'
        '<feMorphology operator="dilate" radius=".25"/>'
        "</filter>"
        '<filter id="gl" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.2"/></filter>'
        '<radialGradient id="hm"><stop offset="0" stop-color="#78144f" stop-opacity=".55"/><stop offset="1" stop-color="#78144f" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="hc"><stop offset="0" stop-color="#0a5a78" stop-opacity=".55"/><stop offset="1" stop-color="#0a5a78" stop-opacity="0"/></radialGradient>'
        '<linearGradient id="top" x2="0" y2="1"><stop offset="0" stop-color="#0a0820" stop-opacity=".8"/><stop offset="1" stop-color="#0a0820" stop-opacity="0"/></linearGradient>'
        + models()
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">'
        f"<style>{style}</style><defs>{defs}</defs>"
        '<g filter="url(#px)">'
        f'<rect width="{W}" height="{H}" fill="{PAVEMENT}"/>'
        f'<g shape-rendering="crispEdges">{"".join(out)}</g>'
        f'<g filter="url(#gl)" opacity=".6" style="mix-blend-mode:screen">{"".join(glow)}</g>'
        '<ellipse cx="20" cy="285" rx="170" ry="140" fill="url(#hm)" style="mix-blend-mode:screen"/>'
        '<ellipse cx="460" cy="20" rx="180" ry="150" fill="url(#hc)" style="mix-blend-mode:screen"/>'
        f'<rect width="{W}" height="70" fill="url(#top)"/>'
        "</g></svg>"
    )


# ---------- output ----------

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome",
    "chromium",
    "microsoft-edge",
]


def preview(scene):
    """Screenshot the scene at 1920 x 1200 with a headless Edge or Chrome."""
    browser = next((b for b in BROWSERS if os.path.isfile(b) or shutil.which(b)), None)
    if browser is None:
        print("No Edge or Chrome found: the preview was not made.")
        return
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "scene.svg"
        page.write_text(scene, encoding="utf-8")
        PREVIEW.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--window-size=1920,1200",
                f"--user-data-dir={Path(tmp) / 'profile'}",
                f"--screenshot={PREVIEW}",
                page.as_uri(),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    print(f"{PREVIEW.relative_to(ROOT)}: 1920 x 1200")


def main():
    scene = svg()
    if len(scene) > MAX_SCENE:
        raise SystemExit(f"The scene is {len(scene)} characters; the app takes at most {MAX_SCENE}.")
    SCENE_MODULE.write_text(
        "// Generated by tools/build.py: edit that, then run\n"
        "//   python night-theme/tools/build.py\n"
        f"export const SCENE = {json.dumps(scene)}\n",
        encoding="utf-8",
    )
    print(f"{SCENE_MODULE.relative_to(ROOT)}: {len(scene)} characters")
    preview(scene)


if __name__ == "__main__":
    main()
