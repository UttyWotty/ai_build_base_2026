// One approved decision's outcome at the demo clock: pending, settled by the failure, or closed with no failure.
// The numbers come from the backend's pricing at the real outcome, the same as the track record.
// Pending outcomes say what they are waiting for, so nobody mistakes them for results.
import type { Outcome } from '../api/types'
import { hours, money, shortTime } from '../lib/format'

export function OutcomeLine({ outcome }: { outcome: Outcome | undefined }) {
  if (!outcome) return null
  if (outcome.status === 'pending') {
    return <div className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">Outcome pending: move the clock past the failure or the end of the warning window to see it.</div>
  }
  if (outcome.status === 'failed') {
    return (
      <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
        Failed as predicted at {shortTime(outcome.settled_at ?? '')}: down <b>{hours(outcome.with_plan_hours)}</b> with the plan
        instead of {hours(outcome.without_plan_hours)}. <b>{money(outcome.usd_saved)}</b> saved.
      </div>
    )
  }
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
      No failure within the warning window (closed {shortTime(outcome.settled_at ?? '')}); {money(outcome.extra_cost_usd)} spent as a precaution.
    </div>
  )
}
