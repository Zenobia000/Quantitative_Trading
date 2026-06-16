import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { CommandPalette } from './CommandPalette'

function renderPalette(onClose = vi.fn()) {
  render(
    <MemoryRouter>
      <CommandPalette open onClose={onClose} />
    </MemoryRouter>,
  )
  return onClose
}

describe('CommandPalette', () => {
  it('hidden when closed', () => {
    render(
      <MemoryRouter>
        <CommandPalette open={false} onClose={() => {}} />
      </MemoryRouter>,
    )
    expect(screen.queryByPlaceholderText('搜尋頁面 / 跳轉…')).not.toBeInTheDocument()
  })

  it('lists nav commands and filters by query', () => {
    renderPalette()
    expect(screen.getByText('績效總覽')).toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText('搜尋頁面 / 跳轉…'), { target: { value: '風控' } })
    expect(screen.getByText('風控指標')).toBeInTheDocument()
    expect(screen.queryByText('績效總覽')).not.toBeInTheDocument()
  })

  it('selecting a command closes the palette', () => {
    const onClose = renderPalette()
    fireEvent.click(screen.getByText('部位狀態'))
    expect(onClose).toHaveBeenCalled()
  })

  it('Escape closes', () => {
    const onClose = vi.fn()
    renderPalette(onClose)
    fireEvent.keyDown(screen.getByPlaceholderText('搜尋頁面 / 跳轉…'), { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })

  it('no match shows empty state', () => {
    renderPalette()
    fireEvent.change(screen.getByPlaceholderText('搜尋頁面 / 跳轉…'), { target: { value: 'zzzznope' } })
    expect(screen.getByText('無相符項目')).toBeInTheDocument()
  })
})
