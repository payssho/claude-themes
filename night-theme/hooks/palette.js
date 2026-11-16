import { makeColors } from './make-colors.js'

// Cyberpunk night: indigo surfaces, magenta, cyan and yellow neon.
// Made for dark mode only: a neon city has no daytime version.
export const { theme, problems } = makeColors({
  label: 'Neon city',
  only: 'dark',
  roles: {
    accent: '#ff4fb0', // neon magenta
    danger: '#e4707f',
    success: '#5ee8a0',
    warning: '#ffd23f', // neon yellow
    pro: '#4fd8ff', // neon cyan
  },
  dark: {
    gray: {
      anchors: {
        'surface-0': '#14112a',
        'surface-1': '#1a1632',
        'surface-2': '#201b3b',
        'surface-3': '#241e3f',
        'text-primary': '#efe7f8',
        'text-secondary': '#c8bddf',
        'text-muted': '#a196bd',
      },
    },
  },
})
