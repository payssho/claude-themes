import type { EngineInterface, Register, ThemeSetArgs } from 'claude-code'

import { problems, theme } from './palette.js'
import { SCENE } from './scene.js'

const SCENE_NAME = 'night-city'

// The city is a still SVG, drawn by the ui.render hook below as a plain
// picture: no animation runs, so it costs nothing once drawn.
const LOOK: ThemeSetArgs = {
  colors: theme,
  backdrop: {
    scene: SCENE_NAME,
    // Panels frosted in the theme's own indigo, so the city glows through softly.
    glass: { blur: 18, tint: '#14112a', opacity: 0.62 },
  },
}

// Remembered across sessions, so the theme comes back on its own once chosen.
const ENABLED = 'enabled'

async function turnOn($: EngineInterface): Promise<string> {
  const unpainted = problems.find(line => line.startsWith("Desktop won't paint"))

  if (unpainted !== undefined) {
    $.ui.toast(unpainted)
  }
  const set = await $.theme.set(LOOK)

  return set.isDrawn ? 'Night theme on.' : `Night theme set, but not drawn here: ${set.reason}`
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'night-theme',
      description: 'Shows the neon night city behind the conversation. "/night-theme off" puts the app\'s own look back.',
    })
    if ((await $.store.get(ENABLED)) === true) {
      await turnOn($)
    }

    return next(e)
  })

  on('command.run', { command: 'night-theme' }, async ($, e) => {
    if (e.args.trim().toLowerCase() === 'off') {
      await $.store.set(ENABLED, false)
      await $.theme.clear()

      return { text: 'Night theme off.' }
    }
    await $.store.set(ENABLED, true)

    return { text: await turnOn($) }
  })

  on('ui.render', { component: 'Backdrop' }, ($, e, next) => {
    if ((e.surface !== 'desktop' && e.surface !== 'mobile') || e.props.scene !== SCENE_NAME) {
      return next(e)
    }
    const { Svg } = $.ui.resolve(e)

    return (
      <Svg
        source={SCENE}
        alt="A tiny pixel-art cyberpunk city at night seen from above: neon towers, shops, cafés, parks and two elevated metro lines."
      />
    )
  })
}
