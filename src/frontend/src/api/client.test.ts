// Tests for how a failed request becomes the message the page shows: the backend's detail when it sent one.
// FastAPI validation errors arrive as a list and are joined; a body without a detail falls back to the status code.
// The message is never empty, because HTTP/2 responses carry no status text.
import { describe, expect, it } from 'vitest'
import { errorDetail } from './client'

describe('errorDetail', () => {
  it('uses the backend detail, joins validation issues, and never returns an empty message', () => {
    expect(errorDetail({ detail: 'Unknown alert AL-9' }, 404, '')).toBe('Unknown alert AL-9')
    expect(errorDetail({ detail: [{ msg: 'String should have at most 8000 characters' }] }, 422, ''))
      .toBe('The request was not accepted: String should have at most 8000 characters')
    expect(errorDetail(null, 500, '')).toBe('The server answered 500. Try again in a moment.')
    expect(errorDetail({}, 502, 'Bad Gateway')).toBe('The server answered 502 Bad Gateway. Try again in a moment.')
  })
})
