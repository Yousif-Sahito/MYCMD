import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import App from './App'

beforeEach(() => {
  window.history.pushState({}, '', '/')
  localStorage.clear()
})

describe('MYCMD portfolio application', () => {
  it('renders home and navigates to projects', async () => {
    const user = userEvent.setup()
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Build. Operate. Explore.' })).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Projects' }))
    expect(await screen.findByRole('heading', { name: 'Projects' })).toBeInTheDocument()
  })

  it('filters project cards', async () => {
    window.history.pushState({}, '', '/projects')
    const user = userEvent.setup()
    render(<App />)
    const search = await screen.findByLabelText('Search')
    await user.type(search, 'terminal')
    expect(screen.getByRole('heading', { name: 'MYCMD Terminal Engine' })).toBeInTheDocument()
  })

  it('shows 404 recovery', async () => {
    window.history.pushState({}, '', '/missing')
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})
