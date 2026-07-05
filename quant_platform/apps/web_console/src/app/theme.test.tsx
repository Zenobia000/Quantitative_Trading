import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ThemeProvider, useTheme, THEME_KEY } from './theme'

function Probe() {
  const { mode, resolved, setMode } = useTheme()
  return (
    <div>
      <span data-testid="mode">{mode}</span>
      <span data-testid="resolved">{resolved}</span>
      <button onClick={() => setMode('light')}>go-light</button>
      <button onClick={() => setMode('system')}>go-system</button>
    </div>
  )
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.className = ''
    document.documentElement.style.colorScheme = ''
  })

  it('未儲存時預設 dark 並掛 .dark', () => {
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    )
    expect(screen.getByTestId('mode').textContent).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('setMode 持久化並切換 documentElement class', () => {
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    )
    fireEvent.click(screen.getByText('go-light'))
    expect(localStorage.getItem(THEME_KEY)).toBe('light')
    expect(document.documentElement.classList.contains('light')).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(document.documentElement.style.colorScheme).toBe('light')
  })

  it('system 模式由 matchMedia 推導（mock matches:false → light）', () => {
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    )
    fireEvent.click(screen.getByText('go-system'))
    expect(screen.getByTestId('mode').textContent).toBe('system')
    expect(screen.getByTestId('resolved').textContent).toBe('light')
  })
})
