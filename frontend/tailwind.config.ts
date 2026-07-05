import type { Config } from 'tailwindcss'

// Wall Street operations console tokens. Values live in src/styles/tokens.css.
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: 'var(--bg-base)',
        surface: 'var(--bg-surface)',
        input: 'var(--bg-input)',
        code: 'var(--bg-code)',
        'surface-raised': 'var(--bg-raised)',
        panel: 'var(--bg-panel)',
        row: 'var(--bg-row)',
        border: 'var(--border-default)',
        'border-strong': 'var(--border-strong)',
        scrim: 'var(--scrim)',
        text: {
          DEFAULT: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
        },
        gain: 'var(--gain)',
        loss: 'var(--loss)',
        'loss-aaa': 'var(--loss-aaa)',
        warning: 'var(--warning)',
        error: 'var(--error)',
        info: 'var(--info)',
        halt: 'var(--halt)',
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans TC', 'system-ui', 'sans-serif'],
        mono: ['Geist Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        pill: '9999px',
        lg: '12px',
        md: '8px',
        sm: '4px',
      },
      boxShadow: {
        // flat 分層：本系統無陰影，一律 1px border
        none: 'none',
      },
      ringColor: {
        focus: 'var(--focus-ring)',
      },
    },
  },
  plugins: [],
} satisfies Config
