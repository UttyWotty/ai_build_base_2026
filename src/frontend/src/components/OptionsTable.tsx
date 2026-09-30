// Every way to get the spare for one alert, priced: extra spend, downtime, worst case, lost contribution, customers.
// The rules' recommendation is highlighted; the numbers are exactly those the agent sees.
// Totals are extra spend plus lost contribution, the cost beyond a normal planned repair.
import { Star } from 'lucide-react'
import type { RecoveryOption } from '../api/types'
import { hours, money, optionLabel, shortTime } from '../lib/format'

const HEADERS = ['Option', 'Source', 'Spare ready', 'Extra cost', 'Downtime', 'Worst case', 'Lost contribution', 'Customer lines', 'Total']

export function OptionsTable({ options }: { options: RecoveryOption[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
            {HEADERS.map((h) => <th key={h} className="whitespace-nowrap px-3 py-2 font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {options.map((o) => (
            <tr key={`${o.kind}-${o.source}`} className={`border-b border-slate-100 ${o.recommended_by_rules ? 'bg-brand-50/60' : ''}`}>
              <td className="whitespace-nowrap px-3 py-2 font-medium">
                <span className="inline-flex items-center gap-1.5">
                  {o.recommended_by_rules && <Star className="h-3.5 w-3.5 fill-brand-600 text-brand-600" />}
                  {optionLabel(o.kind)}
                </span>
              </td>
              <td className="whitespace-nowrap px-3 py-2 font-mono text-xs">{o.source}</td>
              <td className="whitespace-nowrap px-3 py-2 tabular-nums">{shortTime(o.ready_at)}</td>
              <td className="px-3 py-2 tabular-nums">{money(o.extra_cost_usd)}</td>
              <td className="px-3 py-2 tabular-nums">{hours(o.downtime_hours)}</td>
              <td className="px-3 py-2 tabular-nums text-slate-500">{hours(o.worst_case_downtime_hours)}</td>
              <td className={`px-3 py-2 tabular-nums ${o.lost_contribution_usd > 0 ? 'text-rose-700' : ''}`}>{money(o.lost_contribution_usd)}</td>
              <td className="px-3 py-2 tabular-nums">{o.customer_lines_at_risk}</td>
              <td className="px-3 py-2 font-semibold tabular-nums">{money(o.total_cost_usd)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
