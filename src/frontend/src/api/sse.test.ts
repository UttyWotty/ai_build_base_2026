// Tests for the server-sent events parser, which must survive events split across network chunks.
// Complete events come out in order; an unfinished tail is kept for the next chunk.
// Lines that are not data lines (comments, blank keep-alives) are ignored.
import { describe, expect, it } from 'vitest'
import { parseSse } from './sse'

describe('parseSse', () => {
  it('returns complete events and keeps the unfinished tail', () => {
    const first = parseSse('data: {"a":1}\n\ndata: {"b"')
    expect(first.events).toEqual(['{"a":1}'])
    const second = parseSse(first.rest + ':2}\n\n')
    expect(second.events).toEqual(['{"b":2}'])
    expect(second.rest).toBe('')
  })

  it('ignores comments and keep-alive lines', () => {
    expect(parseSse(': ping\n\ndata: x\n\n').events).toEqual(['x'])
  })
})
