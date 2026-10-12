// Tests for composing an in-place conversation turn: the topic always leads, then recent turns, then the question.
// Only the last few turns ride along, and long earlier answers are trimmed with an ellipsis.
// A first question carries no history block at all.
import { describe, expect, it } from 'vitest'
import { ANSWER_CHARS, HISTORY_TURNS, composeQuestion, trimAnswer } from './conversation'

describe('conversation', () => {
  it('sends the topic and the question alone on the first turn', () => {
    expect(composeQuestion(' Alert A1 ', [], ' Is it worn? ')).toBe('Topic: Alert A1\n\nQuestion: Is it worn?')
  })

  it('carries only the most recent turns', () => {
    const history = Array.from({ length: HISTORY_TURNS + 2 }, (_, i) => ({ question: `q${i}`, answer: `a${i}` }))
    const text = composeQuestion('T', history, 'next')
    expect(text).not.toContain('Q: q0')
    expect(text).not.toContain('Q: q1')
    expect(text).toContain(`Q: q${HISTORY_TURNS + 1}\nA: a${HISTORY_TURNS + 1}`)
    expect(text.endsWith('Question: next')).toBe(true)
  })

  it('trims long answers to the limit with an ellipsis', () => {
    const long = 'x'.repeat(ANSWER_CHARS + 50)
    const trimmed = trimAnswer(long)
    expect(trimmed.length).toBe(ANSWER_CHARS)
    expect(trimmed.endsWith('...')).toBe(true)
    expect(trimAnswer('short answer')).toBe('short answer')
  })
})
