// Tests for what the live clock does after the autopilot's triages: wait for the rest, hold for a decision, or run on.
// A hold needs the wait switched on and at least one triage that succeeded, since only a success leaves a proposal.
// Failed triages, and the wait switched off, keep the old behaviour of running on once the batch is done.
import { describe, expect, it } from 'vitest'
import type { AgentDoneEvent, PlantEvent } from '../api/types'
import { afterTriages, type Triage } from './live'

const EVENT: PlantEvent = {
  at: '2026-07-25T02:00', kind: 'alert', site_id: 'US1', subject: 'US1-L2-01', title: 'P2 alert', severity: 'warning',
  alert_id: 'AL-1',
}
const SUCCESS = { error_kind: '' } as AgentDoneEvent
const OVERLOADED = { error_kind: 'overloaded' } as AgentDoneEvent

const triage = (done: boolean, result?: AgentDoneEvent | null): Triage => ({ event: EVENT, done, result })

describe('afterTriages', () => {
  it('waits while any triage of the batch is still running, or when there is none', () => {
    expect(afterTriages([], true)).toBe('wait')
    expect(afterTriages([triage(true, SUCCESS), triage(false)], true)).toBe('wait')
  })

  it('holds for a decision when the wait is on and a triage succeeded', () => {
    expect(afterTriages([triage(true, SUCCESS)], true)).toBe('hold')
    expect(afterTriages([triage(true, OVERLOADED), triage(true, SUCCESS)], true)).toBe('hold')
  })

  it('runs on when the wait is off or every triage failed', () => {
    expect(afterTriages([triage(true, SUCCESS)], false)).toBe('resume')
    expect(afterTriages([triage(true, OVERLOADED)], true)).toBe('resume')
    expect(afterTriages([triage(true, null)], true)).toBe('resume')
  })
})
