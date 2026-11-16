// A tiny cyberpunk city at night, seen from above and to the side (isometric),
// in a blocky, cube-built, pixel style. Drawn as one SVG, animated with CSS.
//
// Calm by design: nothing drives around. Only lights breathe (shop signs,
// storefronts, a few windows, billboards, beacons), one metro passes on the
// left and one on the right at uneven intervals. The conversation covers the
// middle, so the middle stays plain and still; the detail lives on the left
// and right edges, which stay visible.
//
// Scale: the scene is 1600 units wide and fills a ~1900 px window, so about
// 32 units make a centimetre on screen. Small towers stand ~96 units tall
// (~3 cm), the tallest ~290 (~9 cm); shops and cafés ~1.5 cm.

const W = 1600
const H = 1000
const OX = 800
const OY = -420

function seeded(seed) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
const rnd = seeded(7331)
const rand = (a, b) => a + rnd() * (b - a)
const n = x => Math.round(x * 10) / 10
const pick = list => list[Math.floor(rnd() * list.length)]
const clamp = (x, a, b) => Math.max(a, Math.min(b, x))
const idx = len => Math.floor(rnd() * len)

const NEON = ['#2de2ff', '#ff3ea5', '#9b6bff', '#ffd23f', '#5dff9e', '#ff7a3d']
const FACADES = ['#2a1f55', '#1d2f55', '#3a1f4a', '#1b3a46', '#40223a']
const GLOWS = ['#ffd27a', '#7ff6ff', '#ff8ad8', '#b9ff7a', '#c9a6ff']
const DELAYS = 8 // classes d0..d7 put each light out of step with its neighbours

// ---------- isometric geometry ----------
// Grid (i, j, z): i runs right-down, j runs left-down, z is height in units.

const P = (i, j, z = 0) => [(i - j) * 20, (i + j) * 10 - z]
const pt = (i, j, z = 0) => {
  const [x, y] = P(i, j, z)
  return `${n(x)},${n(y)}`
}
const poly = (pts, attrs) => `<polygon points="${pts.join(' ')}" ${attrs}/>`
const screen = (i, j) => [OX + (i - j) * 20, OY + (i + j) * 10]

// A box: top, left face (+j) and right face (+i), with optional content drawn
// in each face's own flat coordinates (x along the face, y down from its top).
function box(i, j, w, d, z0, z1, o) {
  const h = z1 - z0
  const [lx, ly] = P(i, j + d, z1)
  const [rx, ry] = P(i + w, j + d, z1)
  const lw = n(20 * w)
  const rw = n(20 * d)
  return (
    poly([pt(i, j, z1), pt(i + w, j, z1), pt(i + w, j + d, z1), pt(i, j + d, z1)], `style="fill:${o.top}"`) +
    `<g transform="matrix(1 .5 0 1 ${n(lx)} ${n(ly)})"><rect width="${lw}" height="${h}" style="fill:${o.left}"/>` +
    (o.leftIn ? o.leftIn(20 * w, h) : '') +
    '</g>' +
    `<g transform="matrix(1 -.5 0 1 ${n(rx)} ${n(ry)})"><rect width="${rw}" height="${h}" style="fill:${o.right}"/>` +
    (o.rightIn ? o.rightIn(20 * d, h) : '') +
    (o.shade ? `<rect width="${rw}" height="${h}" fill="#000" opacity="${o.shade}"/>` : '') +
    '</g>'
  )
}

// ---------- patterns ----------

function windowPattern(id, colors, p) {
  let s = `<pattern id="${id}" width="24" height="27" patternUnits="userSpaceOnUse">`
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 3; c++) {
      const fill = rnd() < p ? pick(colors) : '#0c0a1f'
      s += `<rect x="${2 + c * 8}" y="${2 + r * 9}" width="4" height="5" fill="${fill}"/>`
    }
  }
  return s + '</pattern>'
}

const PATTERNS =
  windowPattern('pA', ['#7ff6ff', '#c9fbff', '#2de2ff'], 0.36) +
  windowPattern('pB', ['#ff8ad8', '#ff3ea5', '#c9a6ff'], 0.32) +
  windowPattern('pC', ['#ffd88a', '#ffc46b', '#fff1c4'], 0.38) +
  windowPattern('pD', ['#c9a6ff', '#7ff6ff', '#ffd88a'], 0.45) +
  '<pattern id="pS" width="6" height="40" patternUnits="userSpaceOnUse"><rect width="1" height="40" fill="#000" opacity=".45"/></pattern>'

// ---------- buildings ----------

const HEIGHTS = [64, 96, 128, 176, 224]
const TOWER_PATTERNS = ['pA', 'pB', 'pC']

function roofNeon(a, w, h) {
  const pts = [pt(a, a, h), pt(a + w, a, h), pt(a + w, a + w, h), pt(a, a + w, h)]
  const [fx, fy] = P(a + w, a + w, h)
  return (
    poly(pts, 'fill="none" style="stroke:var(--n)" stroke-width="3" opacity=".3"') +
    poly(pts, 'fill="none" style="stroke:var(--n)" stroke-width="1"') +
    `<path d="M${n(fx)} ${n(fy)}v${h}" style="stroke:var(--n)" stroke-width="1.5" opacity=".9"/>`
  )
}

function antenna(i, j, h) {
  const [x, y] = P(i, j, h)
  return (
    `<path d="M${n(x)} ${n(y)}v-22" stroke="#6a64a8" stroke-width="1"/>` +
    `<rect class="blink" x="${n(x - 1.5)}" y="${n(y - 25)}" width="3" height="3" fill="#ff3b5c"/>`
  )
}

function tower(id, h, pat) {
  const a = 0.2
  const w = 1.6
  const windows = (fw, fh) => `<rect x="2" y="5" width="${n(fw - 4)}" height="${fh - 12}" fill="url(#${pat})"/>`
  // One window per face that slowly goes dark, then lights again.
  const lamp = (fh, c) => `<rect class="wf" x="10" y="${fh - 34}" width="4" height="5" fill="${c}"/>`
  let s = box(a, a, w, w, 0, h, {
    top: '#2d2960',
    left: '#1f1c44',
    right: '#1f1c44',
    shade: 0.42,
    leftIn: (fw, fh) => windows(fw, fh) + (h > 64 ? lamp(fh, '#ffd88a') : ''),
    rightIn: (fw, fh) => windows(fw, fh) + (h > 96 ? lamp(fh, '#7ff6ff') : ''),
  })
  s += roofNeon(a, w, h)
  s += box(a + 0.3, a + 0.25, 0.45, 0.4, h, h + 5, { top: '#3c3778', left: '#26224f', right: '#26224f', shade: 0.35 })
  if (h >= 176) s += antenna(a + 1.15, a + 1.1, h)
  return `<g id="${id}">${s}</g>`
}

// A plain, still tower for the covered middle.
function plainTower(id, h) {
  const dim = (fw, fh) => `<rect x="2" y="5" width="${n(fw - 4)}" height="${fh - 12}" fill="url(#pD)" opacity=".5"/>`
  return `<g id="${id}">${box(0.2, 0.2, 1.6, 1.6, 0, h, { top: '#28244f', left: '#1c1a3c', right: '#1c1a3c', shade: 0.42, leftIn: dim, rightIn: dim })}</g>`
}

// A tower with a billboard that drifts through colours.
function board(id, base, h) {
  const [lx, ly] = P(0.2, 1.8, h)
  return `<g id="${id}"><use href="#${base}"/><g transform="matrix(1 .5 0 1 ${n(lx)} ${n(ly)})"><rect class="bb" x="3" y="7" width="26" height="14"/><rect x="6" y="10" width="12" height="2" fill="#fff" opacity=".7"/><rect x="6" y="14" width="18" height="2" fill="#fff" opacity=".5"/></g></g>`
}

function steppedTower(id, h1, h2, pat) {
  const windows = (fw, fh) => `<rect x="2" y="5" width="${n(fw - 4)}" height="${fh - 12}" fill="url(#${pat})"/>`
  const style = { top: '#2d2960', left: '#1f1c44', right: '#1f1c44', shade: 0.42, leftIn: windows, rightIn: windows }
  let s = box(0.15, 0.15, 1.7, 1.7, 0, h1, style)
  s += roofNeon(0.15, 1.7, h1)
  s += box(0.5, 0.5, 1.0, 1.0, h1, h2, style)
  s += roofNeon(0.5, 1.0, h2)
  s += antenna(1.0, 1.0, h2)
  return `<g id="${id}">${s}</g>`
}

function storefront(fw, fh, g, nn) {
  return (
    `<rect class="gl" x="2" y="${fh - 11}" width="${n(fw - 4)}" height="9" style="fill:var(${g})"/>` +
    `<rect x="2" y="${fh - 11}" width="${n(fw - 4)}" height="9" fill="url(#pS)"/>` +
    `<rect x="1" y="${fh - 14}" width="${n(fw - 2)}" height="3" style="fill:var(${nn})"/>`
  )
}

// Light spilling from a shop onto the pavement, breathing with the shop.
const spill = (j1, j2, v, a) =>
  poly([pt(0.15, j1), pt(1.85, j1), pt(1.85, j2), pt(0.15, j2)], `class="gl" style="fill:var(${v})" fill-opacity="${a}"`)

function shop(id, h) {
  let s = spill(1.85, 2.4, '--g', 0.18)
  s += poly([pt(1.85, 0.15), pt(2.35, 0.15), pt(2.35, 1.85), pt(1.85, 1.85)], 'class="gl" style="fill:var(--g)" fill-opacity=".12"')
  s += box(0.15, 0.15, 1.7, 1.7, 0, h, {
    top: '#2b2754',
    left: 'var(--s)',
    right: 'var(--s)',
    shade: 0.38,
    leftIn: (fw, fh) =>
      storefront(fw, fh, '--g', '--n') +
      `<rect x="5" y="-10" width="17" height="9" style="fill:var(--n)" opacity=".25"/>` +
      `<rect class="sg" x="6" y="-9" width="15" height="7" style="fill:var(--n)"/>` +
      `<rect x="8" y="-7" width="11" height="1" fill="#fff" opacity=".6"/>`,
    rightIn: (fw, fh) => storefront(fw, fh, '--g', '--n'),
  })
  s += box(0.5, 0.4, 0.5, 0.4, h, h + 4, { top: '#3c3778', left: '#26224f', right: '#26224f', shade: 0.35 })
  return `<g id="${id}">${s}</g>`
}

function shops2(id) {
  let s = spill(1.85, 2.35, '--g', 0.18)
  s += box(0.15, 0.15, 1.7, 0.8, 0, 32, {
    top: '#2b2754',
    left: 'var(--s2)',
    right: 'var(--s2)',
    shade: 0.38,
    leftIn: fw => `<rect x="2" y="3" width="${n(fw - 4)}" height="12" fill="url(#pD)"/>`,
    rightIn: (fw, fh) =>
      storefront(fw, fh, '--g2', '--n2') + `<rect x="2" y="3" width="${n(fw - 4)}" height="12" fill="url(#pD)"/>`,
  })
  s += box(0.15, 1.05, 1.7, 0.8, 0, 18, {
    top: '#2b2754',
    left: 'var(--s)',
    right: 'var(--s)',
    shade: 0.38,
    leftIn: (fw, fh) =>
      storefront(fw, fh, '--g', '--n') + `<rect class="sg" x="5" y="-8" width="12" height="6" style="fill:var(--n)"/>`,
    rightIn: (fw, fh) => storefront(fw, fh, '--g', '--n'),
  })
  return `<g id="${id}">${s}</g>`
}

function cafe(id) {
  let s = poly([pt(0.15, 1.65), pt(1.85, 1.65), pt(1.85, 2.45), pt(0.15, 2.45)], 'class="gl" fill="#ffcf7a" fill-opacity=".16"')
  s += box(0.15, 0.15, 1.7, 1.5, 0, 20, {
    top: '#2b2754',
    left: '#3b2340',
    right: '#3b2340',
    shade: 0.38,
    leftIn: (fw, fh) =>
      `<rect class="gl" x="2" y="${fh - 11}" width="${n(fw - 4)}" height="9" fill="#ffcf7a"/>` +
      `<rect x="2" y="${fh - 11}" width="${n(fw - 4)}" height="9" fill="url(#pS)"/>` +
      `<rect x="0" y="${fh - 15}" width="${n(fw)}" height="4" style="fill:var(--n)"/>` +
      // A string of warm bulbs that twinkle softly.
      `<path class="tw" d="M1 ${fh - 16}h${n(fw - 2)}" stroke="#fff3c4" stroke-dasharray="2 3"/>` +
      `<rect class="sg" x="4" y="-9" width="18" height="7" style="fill:var(--n)"/>`,
    rightIn: (fw, fh) => `<rect class="gl" x="2" y="${fh - 11}" width="${n(fw - 4)}" height="9" fill="#ffcf7a"/>`,
  })
  for (const ti of [0.45, 1.2]) {
    s += box(ti, 1.85, 0.16, 0.16, 0, 3, { top: '#d9d4ff', left: '#8a84c0', right: '#8a84c0', shade: 0.3 })
    const [px, py] = P(ti + 0.08, 1.93, 3)
    s += `<path d="M${n(px)} ${n(py)}v-6" stroke="#cfc8ff"/>`
    s += poly([pt(ti - 0.15, 1.93, 9), pt(ti + 0.08, 1.7, 10), pt(ti + 0.31, 1.93, 9), pt(ti + 0.08, 2.16, 8)], 'style="fill:var(--n)"')
  }
  return `<g id="${id}">${s}</g>`
}

function tree(i, j) {
  const [x, y] = P(i, j)
  return (
    `<path d="M${n(x)} ${n(y)}v-5" stroke="#3a2a48" stroke-width="2"/>` +
    box(i - 0.18, j - 0.18, 0.36, 0.36, 5, 14, { top: '#5dffbe', left: '#2fc28e', right: '#2fc28e', shade: 0.4 })
  )
}

function park(id) {
  let s = poly([pt(0.1, 0.1), pt(1.9, 0.1), pt(1.9, 1.9), pt(0.1, 1.9)], 'fill="#10292e"')
  s += `<path d="M${pt(0.1, 1)} L${pt(1.9, 1)}" stroke="#1d3d44" stroke-width="3"/>`
  s += tree(0.5, 0.5) + tree(1.4, 0.45) + tree(0.45, 1.45) + tree(1.45, 1.45)
  const [lx, ly] = P(1.0, 1.0)
  s += `<ellipse class="gl" cx="${n(lx)}" cy="${n(ly)}" rx="18" ry="9" fill="#ffd27a" fill-opacity=".16"/>`
  s += `<path d="M${n(lx)} ${n(ly)}v-12" stroke="#4a4480"/><rect x="${n(lx - 1.5)}" y="${n(ly - 14)}" width="3" height="3" fill="#ffe7a8"/>`
  return `<g id="${id}">${s}</g>`
}

function plaza(id) {
  let s = poly([pt(0.1, 0.1), pt(1.9, 0.1), pt(1.9, 1.9), pt(0.1, 1.9)], 'fill="#28234f"')
  s += poly([pt(0.1, 0.1), pt(1.9, 0.1), pt(1.9, 1.9), pt(0.1, 1.9)], 'fill="none" stroke="#3b3570"')
  s += box(0.65, 0.65, 0.7, 0.7, 0, 3, { top: '#4a4490', left: '#332e66', right: '#332e66', shade: 0.35 })
  s += poly([pt(0.75, 0.75, 3), pt(1.25, 0.75, 3), pt(1.25, 1.25, 3), pt(0.75, 1.25, 3)], 'class="pulse" fill="#2de2ff"')
  const [fx, fy] = P(1, 1, 3)
  s += `<ellipse class="pulse" cx="${n(fx)}" cy="${n(fy)}" rx="22" ry="11" fill="#2de2ff" fill-opacity=".18"/>`
  s += box(0.3, 1.5, 0.4, 0.12, 0, 3, { top: '#6a63b0', left: '#3e3878', right: '#3e3878', shade: 0.3 })
  s += box(1.5, 0.3, 0.12, 0.4, 0, 3, { top: '#6a63b0', left: '#3e3878', right: '#3e3878', shade: 0.3 })
  return `<g id="${id}">${s}</g>`
}

// ---------- metro ----------

function metroTrain(id, sign) {
  let t = ''
  for (let k = 0; k < 4; k++) {
    const i = -2 + k * 1.0
    const front = sign > 0 ? k === 3 : k === 0
    t += box(i, -0.16, 0.94, 0.32, 63, 70, {
      top: '#eef2ff',
      left: '#cdd6f6',
      right: '#cdd6f6',
      shade: 0.35,
      leftIn: (fw, fh) =>
        `<rect x="1" y="1.5" width="${n(fw - 2)}" height="2.5" fill="#2de2ff"/><rect y="${fh - 1}" width="${n(fw)}" height="1" fill="#ff3ea5"/>`,
      rightIn: fw =>
        front && sign > 0
          ? `<rect x="1" y="1.5" width="${n(fw - 2)}" height="2.5" fill="#fff6d0"/>`
          : k === 3
            ? `<rect x="1" y="4" width="${n(fw - 2)}" height="1.5" fill="#ff3b5c"/>`
            : '',
    })
  }
  return `<g id="${id}">${t}</g>`
}

const PERIOD = 8 // 2 cells of road, then a 6 x 6 block of three 2 x 2 lots a side
const N = 150

// The span of a road on screen: along i at j = fixed, or along j at i = fixed.
function visibleRange(fixed, axis) {
  let lo = Infinity
  let hi = -Infinity
  for (let t = -20; t < N + 20; t++) {
    const [x, y] = axis === 'i' ? screen(t, fixed) : screen(fixed, t)
    if (x > -200 && x < W + 200 && y > -160 && y < H + 160) {
      lo = Math.min(lo, t)
      hi = Math.max(hi, t)
    }
  }
  return lo <= hi ? [lo - 3, hi + 3] : null
}

// One elevated line on an i road: pillars, beam, and two trains going opposite
// ways. A train crosses in about a seventh of its cycle, then waits off screen;
// cycles of different lengths make the passes land at uneven intervals.
function metroLine(J, trains) {
  const range = visibleRange(J + 1, 'i')
  if (!range) return ''
  const [lo, hi] = range
  let pillars = ''
  for (let i = Math.ceil(lo / PERIOD) * PERIOD + 1; i < hi; i += PERIOD) {
    const [x, y] = screen(i, J + 1)
    pillars += `M${n(x)} ${n(y)}v-60`
  }
  const beam = box(lo, J + 0.82, hi - lo, 0.36, 59, 63, {
    top: '#3a3578',
    left: '#211d48',
    right: '#211d48',
    shade: 0.3,
    leftIn: (fw, fh) => `<rect y="${fh - 1}" width="${n(fw)}" height="1" fill="#2de2ff" opacity=".85"/>`,
  })
  const len = hi - lo
  let out = `<path d="${pillars}" stroke="#1f1b44" stroke-width="4"/><g transform="translate(${OX} ${OY})">${beam}</g>`
  for (const [sign, cycle, delay] of trains) {
    const [x, y] = screen(sign > 0 ? lo : hi, J + 1)
    out +=
      `<g class="pass" style="--dx:${Math.round(20 * len * sign)}px;--dy:${Math.round(10 * len * sign)}px;animation-duration:${cycle}s;animation-delay:-${delay}s">` +
      `<use href="#metro_${sign > 0 ? 'p' : 'm'}" x="${Math.round(x)}" y="${Math.round(y)}"/></g>`
  }
  return out
}

// The i road whose line runs nearest a screen point.
function roadThrough(x, y) {
  const j1 = (y - OY - (x - OX) / 2) / 20
  return Math.round((j1 - 1) / PERIOD) * PERIOD
}

// ---------- city ----------

function build() {
  let roads = ''
  let lines = ''
  let glows = ''
  const iRoads = []
  const jRoads = []
  for (let r = 0; r < N; r += PERIOD) {
    const ri = visibleRange(r + 1, 'i')
    if (ri) {
      iRoads.push(r)
      roads += poly([pt(ri[0], r), pt(ri[1], r), pt(ri[1], r + 2), pt(ri[0], r + 2)], '')
      lines += `M${pt(ri[0], r + 1)}L${pt(ri[1], r + 1)}`
    }
    const rj = visibleRange(r + 1, 'j')
    if (rj) {
      jRoads.push(r)
      roads += poly([pt(r, rj[0]), pt(r + 2, rj[0]), pt(r + 2, rj[1]), pt(r, rj[1])], '')
      lines += `M${pt(r + 1, rj[0])}L${pt(r + 1, rj[1])}`
    }
  }
  // Coloured light pools at crossings on the edges.
  for (const a of jRoads) {
    for (const b of iRoads) {
      const [x, y] = screen(a + 1, b + 1)
      if (x < -60 || x > W + 60 || y < -60 || y > H + 60) continue
      if (Math.abs(x - OX) < 380 || rnd() > 0.55) continue
      glows += `<ellipse cx="${Math.round(x)}" cy="${Math.round(y)}" rx="38" ry="19" fill="${pick(NEON)}" opacity=".13"/>`
    }
  }

  // A metro on the left and one on the right.
  const left = roadThrough(200, 640)
  const right = roadThrough(1400, 380)
  const metroRows = {
    [left]: metroLine(left, [
      [1, 71, 4],
      [-1, 83, 46],
    ]),
    [right]: metroLine(right, [
      [1, 77, 5],
      [-1, 89, 63],
    ]),
  }

  // Lots, row by row along j (a valid back-to-front order for grid boxes).
  let city = ''
  for (let j0 = 0; j0 < N; j0 += 2) {
    const m = j0 % PERIOD
    if (m === 0) continue // road rows hold no lots
    if (m === 2) city += metroRows[j0 - 2] || ''
    for (let i0 = 0; i0 < N; i0 += 2) {
      if (i0 % PERIOD === 0) continue
      const [x, y] = screen(i0, j0)
      // 0 in the covered middle, 1 on the visible edges.
      const side = clamp((Math.abs(x - OX) - 350) / 90, 0, 1)
      let href
      let cls = ''
      let top = 40
      if (side < 0.5) {
        // Middle: sparse, low and still.
        if (rnd() < 0.82) continue
        const hi = rnd() < 0.7 ? 0 : 1
        href = `pt${hi}`
        top = HEIGHTS[hi] + 10
      } else {
        // Edges: fewer towers, more small detailed places.
        const r = rnd()
        const d = `d${idx(DELAYS)}`
        if (r < 0.36) {
          const kind = rnd()
          if (kind < 0.3) {
            href = 'cafe'
            cls = `n${idx(NEON.length)} ${d}`
          } else if (kind < 0.6) {
            href = 'shops2'
            cls = `k${idx(5)} q${idx(5)} ${d}`
          } else {
            href = rnd() < 0.5 ? 'shopA' : 'shopB'
            cls = `k${idx(5)} ${d}`
          }
        } else if (r < 0.52) {
          href = 'park'
          cls = d
        } else if (r < 0.61) {
          href = 'plaza'
          cls = d
        } else if (r < 0.75) {
          continue
        } else {
          const hi = Math.min(4, Math.floor(rnd() * 5))
          top = HEIGHTS[hi] + 40
          if (hi >= 3 && rnd() < 0.3) href = `st${hi}`
          else href = `t${hi}${pick(TOWER_PATTERNS)}${hi >= 2 && rnd() < 0.2 ? 'b' : ''}`
          cls = `${rnd() < 0.4 ? `n${idx(NEON.length)}` : 'nd'} ${d}`
        }
      }
      if (x + 45 < 0 || x - 45 > W || y + 42 < 0 || y - top > H) continue
      const at = `x="${Math.round(x)}" y="${Math.round(y)}"`
      city += `<use href="#${href}" ${at}${cls ? ` class="${cls}"` : ''}/>`
      for (const [layer, anim] of LIGHTS[href] || []) {
        // Few moving lights keep it calm and light to draw: only some
        // windows and storefronts breathe; signs, boards and beacons all do.
        if ((anim === 'wf' && rnd() > 0.35) || (anim === 'gl' && rnd() > 0.5)) continue
        city += `<use href="#${layer}" ${at} class="${cls} ${anim}"/>`
      }
    }
  }

  return (
    `<g fill="#0e0c22" transform="translate(${OX} ${OY})">${roads}</g>` +
    `<path d="${lines}" stroke="#3b3480" stroke-width="1" stroke-dasharray="6 7" fill="none" transform="translate(${OX} ${OY})"/>` +
    glows +
    city
  )
}

// ---------- light layers ----------
// The app draws the scene in a sandboxed frame where animations inside <use>
// copies don't run. So each prototype is split in two: its still body, and
// one layer per kind of light (signs, storefronts, windows, ...). Every lot
// places the body, then each light layer as its own <use>, and the animation
// runs on that <use> itself, in the main document, where it does run.

const ANIM = new Set(['sg', 'gl', 'wf', 'tw', 'bb', 'blink', 'pulse'])
const LIGHTS = {} // prototype id -> [[light layer id, animation class]]

function parse(src) {
  const re = /<(\/?)([a-zA-Z]+)([^>]*?)(\/?)>/g
  const root = { children: [] }
  const stack = [root]
  let m
  while ((m = re.exec(src))) {
    const [, close, tag, attrs, self] = m
    if (close) {
      stack.pop()
      continue
    }
    const node = { tag, attrs, children: [] }
    stack[stack.length - 1].children.push(node)
    if (!self) stack.push(node)
  }
  return root.children
}

const animOf = node => {
  const m = node.attrs.match(/ class="(\w+)"/)
  return m && ANIM.has(m[1]) ? m : null
}

// keep === null: the still body; otherwise only the lights of that class.
function emit(nodes, keep) {
  let s = ''
  for (const node of nodes) {
    if (node.tag === 'g') {
      const inner = emit(node.children, keep)
      if (keep !== null && !inner) continue
      s += `<g${node.attrs}>${inner}</g>`
      continue
    }
    const m = animOf(node)
    if (keep === null) {
      if (!m) s += `<${node.tag}${node.attrs}/>`
    } else if (m && m[1] === keep) {
      s += `<${node.tag}${node.attrs.replace(m[0], '')}/>`
    }
  }
  return s
}

function split(proto) {
  const [g] = parse(proto)
  const id = g.attrs.match(/id="([^"]+)"/)[1]
  const found = new Set()
  const walk = nodes => {
    for (const node of nodes) {
      if (node.tag === 'g') walk(node.children)
      else if (animOf(node)) found.add(animOf(node)[1])
    }
  }
  walk(g.children)
  LIGHTS[id] = []
  let out = `<g id="${id}">${emit(g.children, null)}</g>`
  for (const c of found) {
    out += `<g id="${id}_${c}">${emit(g.children, c)}</g>`
    LIGHTS[id].push([`${id}_${c}`, c])
  }
  return out
}

const TOWERS = HEIGHTS.map((h, hi) =>
  TOWER_PATTERNS.map(p => split(tower(`t${hi}${p}`, h, p)) + split(board(`t${hi}${p}b`, `t${hi}${p}`, h))).join(''),
).join('')
// A billboard tower also keeps its tower's own lights.
HEIGHTS.forEach((h, hi) =>
  TOWER_PATTERNS.forEach(p => {
    LIGHTS[`t${hi}${p}b`] = [...LIGHTS[`t${hi}${p}`], ...LIGHTS[`t${hi}${p}b`]]
  }),
)

const DEFS =
  '<defs>' +
  PATTERNS +
  TOWERS +
  plainTower('pt0', 64) +
  plainTower('pt1', 96) +
  plainTower('pt2', 128) +
  [
    steppedTower('st3', 96, 176, 'pA'),
    steppedTower('st4', 128, 224, 'pB'),
    shop('shopA', 22),
    shop('shopB', 28),
    shops2('shops2'),
    cafe('cafe'),
    park('park'),
    plaza('plaza'),
  ]
    .map(split)
    .join('') +
  metroTrain('metro_p', 1) +
  metroTrain('metro_m', -1) +
  '<linearGradient id="haze" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a0820" stop-opacity=".9"/><stop offset="1" stop-color="#0a0820" stop-opacity="0"/></linearGradient>' +
  '<radialGradient id="glowM"><stop offset="0" stop-color="#ff3ea5" stop-opacity=".2"/><stop offset="1" stop-color="#ff3ea5" stop-opacity="0"/></radialGradient>' +
  '<radialGradient id="glowC"><stop offset="0" stop-color="#2de2ff" stop-opacity=".16"/><stop offset="1" stop-color="#2de2ff" stop-opacity="0"/></radialGradient>' +
  '</defs>'

const COLOUR_CLASSES =
  NEON.map((c, k) => `.n${k}{--n:${c}}`).join('') +
  '.nd{--n:#3a3474}' +
  [0, 1, 2, 3, 4]
    .map(
      k =>
        `.k${k}{--s:${FACADES[k]};--g:${GLOWS[k]};--n:${NEON[k]}}` +
        `.q${k}{--s2:${FACADES[4 - k]};--g2:${GLOWS[(k + 2) % 5]};--n2:${NEON[(k + 3) % 6]}}`,
    )
    .join('') +
  Array.from({ length: DELAYS }, (_, k) => `.d${k}{--d:-${(k * 1.7).toFixed(1)}s}`).join('')

// Every light moves slowly and softly, out of step with its neighbours.
const STYLE = `
svg{shape-rendering:crispEdges}
ellipse{shape-rendering:auto}
.sg{animation:sg 6s ease-in-out infinite;animation-delay:var(--d,0s)}
@keyframes sg{0%,100%{opacity:1}50%{opacity:.55}}
.gl{animation:gl 9s ease-in-out infinite;animation-delay:var(--d,0s)}
@keyframes gl{0%,100%{opacity:1}50%{opacity:.7}}
.wf{animation:wf 26s ease-in-out infinite;animation-delay:var(--d,0s)}
@keyframes wf{0%,40%,90%,100%{opacity:1}50%,80%{opacity:0}}
.tw{animation:tw 4s ease-in-out infinite;animation-delay:var(--d,0s)}
@keyframes tw{0%,100%{opacity:.9}50%{opacity:.4}}
.bb{animation:bb 28s ease-in-out infinite;animation-delay:var(--d,0s)}
@keyframes bb{0%,100%{fill:#ff3ea5}25%{fill:#9b6bff}50%{fill:#2de2ff}75%{fill:#ffd23f}}
.blink{animation:blink 3.2s ease-in-out infinite;animation-delay:var(--d,0s)}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.15}}
.pulse{animation:pulse 6s ease-in-out infinite;animation-delay:var(--d,0s)}
@keyframes pulse{0%,100%{opacity:.6}50%{opacity:1}}
.pass{animation:pass linear infinite}
@keyframes pass{0%{transform:translate(0,0)}14%,100%{transform:translate(var(--dx),var(--dy))}}
${COLOUR_CLASSES}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
`

const SCENE_TEMPLATE =
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice">` +
  `<style>${STYLE}</style>` +
  DEFS +
  `<rect width="${W}" height="${H}" fill="#1a1736"/>` +
  build() +
  `<circle cx="200" cy="760" r="420" fill="url(#glowM)"/>` +
  `<circle cx="1400" cy="260" r="460" fill="url(#glowC)"/>` +
  `<rect width="${W}" height="240" fill="url(#haze)"/>` +
  '</svg>'

export const SCENE = SCENE_TEMPLATE
