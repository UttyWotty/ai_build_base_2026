// Tests for the verdict confirmation text: it must name the asset and the readable failure mode.
// The prompt is the only guard between a click and a recorded verdict, so its wording is pinned here.
// No React and no network are involved.
import { describe, expect, it } from 'vitest'
import { confirmPrompt } from './verdict'

describe('confirmPrompt', () => {
  it('names the asset and the readable failure mode', () => {
    const prompt = confirmPrompt('US1-L2-01', 'spindle_bearing_wear')
    expect(prompt).toContain('US1-L2-01')
    expect(prompt).toContain('(spindle bearing wear)')
    expect(prompt).toContain('as false?')
  })
})
