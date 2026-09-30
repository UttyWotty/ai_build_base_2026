// Tests for the demo clock arithmetic: advancing across day and month boundaries, formatting, and ordering.
// The clock is UTC wall time, so these must hold on any machine regardless of its time zone.
// Live mode relies on every one of them each second.
import { describe, expect, it } from 'vitest'
import { addHours, isAfter, longClock } from './clockMath'

describe('clockMath', () => {
  it('advances across day and month boundaries', () => {
    expect(addHours('2026-07-31T22:00', 3)).toBe('2026-08-01T01:00')
    expect(addHours('2026-07-25 02:00', 0.5)).toBe('2026-07-25T02:30')
  })

  it('formats the clock for people and orders times', () => {
    expect(longClock('2026-07-25T02:00')).toBe('Sat 25 Jul 2026, 02:00 UTC')
    expect(isAfter('2026-07-25T03:00', '2026-07-25T02:00')).toBe(true)
    expect(isAfter('2026-07-25T02:00', '2026-07-25T02:00')).toBe(false)
  })
})
