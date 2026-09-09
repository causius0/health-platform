import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConfirmDialog } from '../components/ui'

describe('ConfirmDialog', () => {
  it('renders nothing when closed', () => {
    const { container } = render(
      <ConfirmDialog open={false} title="t" message="m" onConfirm={() => {}} onCancel={() => {}} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('confirms with typed input when input mode is on', async () => {
    const onConfirm = vi.fn()
    render(
      <ConfirmDialog open input confirmLabel="Registra esito" title="Chiudere il follow-up"
                     message="Registra l'esito" onConfirm={onConfirm} onCancel={() => {}} />,
    )
    await userEvent.type(screen.getByPlaceholderText(/paziente contattato/), 'Teleconsulto eseguito')
    await userEvent.click(screen.getByText('Registra esito'))
    expect(onConfirm).toHaveBeenCalledWith('Teleconsulto eseguito')
  })
})
