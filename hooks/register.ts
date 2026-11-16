import type { EngineInterface, Register, ThemeSetArgs } from 'claude-code'

import { problems, theme } from './palette.js'

// A still pixel-art picture: the app draws it once and has nothing to animate.
const LOOK: ThemeSetArgs = {
  colors: theme,
  backdrop: { image: { source: 'assets/night-city.png' } },
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
}
