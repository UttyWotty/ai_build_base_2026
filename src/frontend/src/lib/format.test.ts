// Tests for the pure formatting helpers: money, hours, percentages, option labels, and compact dates.
// Missing values must render as an en dash, never as "null" or "NaN".
// Times keep the backend's clock as is; no time-zone conversion happens in the browser.
import { describe, expect, it } from 'vitest'
import { MISSING, compactMoney, hours, modeLabel, money, optionLabel, percent, shortDate, shortTime } from './format'

describe('format', () => {
  it('formats money, hours, and percentages with missing values as a dash', () => {
    expect(money(93174.7)).toBe('$93,175')
    expect(compactMoney(93174.7)).toBe('$93.2k')
    expect(compactMoney(650)).toBe('$650')
    expect(money(-620)).toBe('\u2212$620')
    expect(compactMoney(-35000)).toBe('\u2212$35.0k')
    expect(hours(180.25)).toBe('180.3 h')
    expect(percent(66.14)).toBe('66.1%')
    expect([money(null), hours(undefined), percent(null)]).toEqual([MISSING, MISSING, MISSING])
  })

  it('names options and failure modes for people', () => {
    expect(optionLabel('transfer')).toBe('Air transfer')
    expect(optionLabel('unknown_kind')).toBe('unknown_kind')
    expect(modeLabel('spindle_bearing_wear')).toBe('Spindle bearing wear')
  })

  it('shortens backend timestamps without shifting them', () => {
    expect(shortTime('2026-07-25 02:00')).toBe('25 Jul 02:00')
    expect(shortTime('2026-07-25T02:00')).toBe('25 Jul 02:00')
    expect(shortDate('2026-08-04')).toBe('4 Aug')
    expect(shortTime('soon')).toBe('soon')
  })
})
