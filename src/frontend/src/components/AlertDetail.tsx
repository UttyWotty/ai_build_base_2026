// Everything about one alert at the demo clock: the spare conflict, stock across sites, the supplier's governed record,
// the rules' recommendation against what the site would do alone, every priced option, customers, and sensor evidence.
// The "Draft the plan" button runs the Gemini agent on this alert and streams its work into the panel.
import { Bot, Package, Truck } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client'
import type { Impact } from '../api/types'
import { hours, modeLabel, money, optionLabel, percent, shortTime } from '../lib/format'
import { useAsync } from '../state/useAsync'
import { AgentRunView } from './AgentRunView'
import { OptionsTable } from './OptionsTable'
import { SensorChart } from './SensorChart'
import { Callout, Card, ErrorNote, Loading, Stat } from './ui'

export function AlertDetail({ alertId, asOf }: { alertId: string; asOf: string }) {
  const impact = useAsync(() => api.impact(alertId, asOf), [alertId, asOf])
  const evidence = useAsync(() => api.evidence(alertId, asOf), [alertId, asOf])
  const [planning, setPlanning] = useState(0)
  if (impact.error) return <ErrorNote message={impact.error} />
  if (!impact.data) return <Loading label="Analysing impact" />
  const data = impact.data
  const best = data.options.find((o) => o.recommended_by_rules) ?? data.options[0]
  const question = `Prepare the action plan for alert ${alertId}. Choose the best option, explain why in two sentences, and create the proposal.`
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">{data.alert.asset_id} · {modeLabel(data.alert.failure_mode)}</h2>
          <p className="text-sm text-slate-500">
            Line {data.line.line_id}, raised {shortTime(data.alert.raised_at)}, repair by {shortTime(data.alert.repair_deadline)}, {data.repair_hours} h repair
          </p>
        </div>
        <button onClick={() => setPlanning((n) => n + 1)}
          className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700">
          <Bot className="h-4 w-4" />Draft the plan with the copilot
        </button>
      </div>
      {data.conflict && <Callout>{data.conflict}</Callout>}
      {planning > 0 && (
        <Card title={<span className="inline-flex items-center gap-2"><Bot className="h-4 w-4 text-brand-600" />Copilot · live</span>}>
          <AgentRunView key={planning} question={question} asOf={asOf} />
        </Card>
      )}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <SpareCard data={data} />
        <SupplierCard data={data} />
        <Card title="Recommended by the rules">
          <Stat label={`${optionLabel(best.kind, best.source)} · ${best.source.startsWith('DEC-') ? 'approved' : best.source}`} value={money(best.total_cost_usd)}
            sub={`Spare ready ${shortTime(best.ready_at)} · ${hours(best.downtime_hours)} down`} />
          {data.baseline.kind !== best.kind && (
            <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
              Without the plan ({optionLabel(data.baseline.kind).toLowerCase()}): {hours(data.baseline.downtime_hours)} down,
              {' '}{money(data.baseline.total_cost_usd)}, {data.baseline.customer_lines_at_risk} customer lines at risk.
            </p>
          )}
        </Card>
      </div>
      <Card title="Every way to get the spare"><OptionsTable options={data.options} /></Card>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Why the model raised it">
          {evidence.data ? (
            <div className="space-y-4">
              {evidence.data.sensors.map((s) => <SensorChart key={s.sensor} series={s} />)}
              <p className="text-xs text-slate-500">P-F interval {evidence.data.pf_interval_days} days. {evidence.data.recommended_action}</p>
            </div>
          ) : <Loading label="Reading sensors" />}
        </Card>
        <CustomersCard data={data} />
      </div>
    </div>
  )
}

function SpareCard({ data }: { data: Impact }) {
  if (!data.spare) return <Card title="Spare"><p className="text-sm text-slate-500">This repair needs no spare part.</p></Card>
  const { local, sister_sites: sisters } = data.spare
  return (
    <Card title={<span className="inline-flex items-center gap-2"><Package className="h-4 w-4" />{data.spare.label}</span>}>
      <Stat label={`On hand at ${local.site_id}`} value={local.on_hand} sub={`${local.alerts_queued_for_this_spare.length} alerts queued for it`} />
      <ul className="mt-3 space-y-1 text-xs text-slate-600">
        {sisters.map((s) => <li key={s.site_id}>{s.site_id}: {s.on_hand} on hand, {s.alerts_queued_for_this_spare.length} queued</li>)}
        {local.open_orders.map((o) => <li key={o.po_id}>Open order {o.po_id}: promised {shortTime(o.promised)}, expected {shortTime(o.expected)}</li>)}
      </ul>
    </Card>
  )
}

function SupplierCard({ data }: { data: Impact }) {
  if (!data.supplier) return <Card title="Supplier"><p className="text-sm text-slate-500">No supplier involved.</p></Card>
  const s = data.supplier
  return (
    <Card title={<span className="inline-flex items-center gap-2"><Truck className="h-4 w-4" />{s.name}</span>}>
      <Stat label={`On time, last ${s.window_days} days`} value={percent(s.on_time_percent)} sub={`Expected ${s.expected_days_late} days late`} />
      <p className="mt-3 text-xs text-slate-500">
        Governed metric <code className="font-mono">{s.governed_metric}</code>, SQL fingerprint <code className="font-mono">{s.sql_fingerprint}</code>
      </p>
    </Card>
  )
}

function CustomersCard({ data }: { data: Impact }) {
  const orders = data.baseline.orders_at_risk
  return (
    <Card title="Customer lines at risk without the plan">
      {orders.length === 0 ? <p className="text-sm text-slate-500">None: the line's customers are covered either way.</p> : (
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="py-1">Order line</th><th>Customer</th><th>Part</th><th className="text-right">Qty</th><th className="text-right">Due</th>
          </tr></thead>
          <tbody>{orders.map((o) => (
            <tr key={o.so_line_id} className="border-t border-slate-100">
              <td className="py-1.5 font-mono text-xs">{o.so_line_id}</td><td>{o.customer}</td>
              <td className="font-mono text-xs">{o.part_id}</td><td className="text-right tabular-nums">{o.quantity}</td>
              <td className="text-right tabular-nums">{o.committed}</td>
            </tr>))}
          </tbody>
        </table>
      )}
    </Card>
  )
}
