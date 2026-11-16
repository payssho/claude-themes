// Writes the city as a still SVG, ready to be screenshotted by render.py.
// Every animation is paused where its delay puts it, so each light keeps its
// own brightness and each billboard its own colour, and the metros stop on
// their lines. Edges are made crisp everywhere for the pixel-art look.
//
//   node tools/export-svg.mjs <out.svg>

import { writeFileSync } from 'node:fs'

import { SCENE } from './scene.js'

const out = process.argv[2]
if (!out) {
  console.error('usage: node tools/export-svg.mjs <out.svg>')
  process.exit(1)
}

const FREEZE = '<style>*{animation-play-state:paused!important;shape-rendering:crispEdges!important}</style>'

writeFileSync(out, SCENE.replace('</style>', `</style>${FREEZE}`))
