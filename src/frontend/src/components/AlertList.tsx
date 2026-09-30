// The list of open alerts at the demo clock, each with its priority, deadline, conflict flag, and the rules' pick.
// Clicking an alert selects it for the detail panel; the selected card is highlighted.
// Cards are ordered as the backend returns them: earliest repair deadline first.
import { AlertTriangle } from 'lucide-react'
import type { OverviewAlert } from '../api/types'
import { modeLabel, money, optionLabel, shortTime } from '../lib/format'
import { Badge } from './ui'

export function AlertList({ alerts, selected, onSelect }:
  { alerts: OverviewAlert[]; selected: string | null; onSelect: (id: string) => void }) {
  return (
    <div className="space-y-2">
      {alerts.map((a) => (
        <button key={a.alert_id} onClick={() => onSelect(a.alert_id)}
          className={`w-full rounded-xl border px-4 py-3 text-left transition ${a.alert_id === selected
            ? 'border-brand-500 bg-brand-50/60 ring-1 ring-brand-500' : 'border-slate-200 bg-white hover:border-slate-300'}`}>
          <div className="flex items-center gap-2">
            <Badge tone={a.priority === 'P1' ? 'danger' : 'neutral'}>{a.priority}</Badge>
            <span className="font-semibold">{a.asset_id}</span>
            {a.conflict && <AlertTriangle className="ml-auto h-4 w-4 text-amber-600" aria-label="Spare conflict" />}
          </div>
          <div className="mt-1 text-sm text-slate-700">{modeLabel(a.failure_mode)}</div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
            <span>Repair by {shortTime(a.repair_deadline)}</span>
            <span className="font-medium text-slate-700">{optionLabel(a.recommended.kind)} · {money(a.recommended.total_cost_usd)}</span>
          </div>
        </button>
      ))}
    </div>
  )
}
