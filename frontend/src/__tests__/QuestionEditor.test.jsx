import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import QuestionEditor, { serializeAnswer } from '../components/QuestionEditor'

const smokingQuestion = {
  id: 1,
  prompt: 'Fumazione',
  answer_type: 'single_choice',
  options: [
    { value: 'Mai fumato', label: 'Mai fumato', protective: true },
    { value: 'Fumatore/a attuale', label: 'Fumatore/a attuale', risk: true },
  ],
}

describe('QuestionEditor', () => {
  it('renders options with risk/protective flags', () => {
    render(<QuestionEditor question={smokingQuestion} value={null} onChange={() => {}} />)
    expect(screen.getByText('Mai fumato')).toBeInTheDocument()
    expect(screen.getByText('fattore di rischio')).toBeInTheDocument()
    expect(screen.getByText('protettivo')).toBeInTheDocument()
  })

  it('reports the selected single-choice value', async () => {
    const onChange = vi.fn()
    render(<QuestionEditor question={smokingQuestion} value={null} onChange={onChange} />)
    await userEvent.click(screen.getAllByRole('radio')[0])
    expect(onChange).toHaveBeenCalledWith('Mai fumato')
  })
})

describe('serializeAnswer', () => {
  it('joins multi-choice arrays', () => {
    expect(serializeAnswer(['Influenzale', 'COVID-19'])).toBe('Influenzale, COVID-19')
  })
  it('trims free text', () => {
    expect(serializeAnswer('  Nessuna nota  ')).toBe('Nessuna nota')
  })
})
