import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Placeholder } from '@/components/Placeholder'

describe('scaffold smoke', () => {
  it('renders a placeholder page with route + spec refs', () => {
    render(<Placeholder title="首頁 · 控制塔" route="/" spec="home_overview" />)
    expect(screen.getByText('首頁 · 控制塔')).toBeInTheDocument()
    expect(screen.getByText('Phase 2 待建')).toBeInTheDocument()
    expect(screen.getByText('/')).toBeInTheDocument()
  })
})
