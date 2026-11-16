# Night theme for Claude

A tiny cyberpunk city at night, in pixel art, behind your Claude conversation:
blocky neon towers, little shops and cafés with glowing storefronts, parks,
plazas and two elevated metro lines. The middle of the city stays calm and
dark, where the conversation sits; the detail lives on the left and right
edges, which stay visible. The interface gets a matching indigo palette with
magenta, cyan and yellow neon.

The background is completely still, drawn by the app as a plain picture, so
it has nothing to animate or redraw: it costs nothing in performance.

![The night city](assets/night-city.png)

## Install

At the prompt of a Claude Code terminal session:

```
/plugin install night-theme --marketplace payssho/claude-themes
```

Answer `y` to add the marketplace, then pick a scope.

From a shell:

```bash
claude plugin install night-theme --marketplace payssho/claude-themes
```

In the desktop app, where `/plugin` does not run: click **+** next to the
prompt box, then **Plugins**, **Add marketplace** with
`payssho/claude-themes`, then **Add plugin**.

## Use

- `/night-theme` turns the theme on. It is remembered, so it comes back by
  itself in your next sessions.
- `/night-theme off` puts the app's own look back.

The background shows in the desktop and mobile apps. A terminal draws no
background.

## Change the city

The city is generated:

- `tools/scene.js` draws it as an SVG (layout, buildings, colours, metros).
- `tools/export-svg.mjs` freezes it (no animation, crisp pixel edges) into
  `hooks/scene.js`, which the plugin hands to the app as the background.
- `tools/render.py` turns the same SVG into `assets/night-city.png`, the
  pixel-art preview at the top of this page.

From the top of the repository:

```bash
node night-theme/tools/export-svg.mjs night-theme/hooks/scene.js
pip install pillow
python night-theme/tools/render.py
```

Then run `/reload-plugins` and `/night-theme` to see it.

The interface colours are in `hooks/palette.js`.
