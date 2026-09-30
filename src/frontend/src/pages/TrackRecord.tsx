// The track record: every alert of the test period, the copilot's plan against the site acting alone, scored at what
// really happened. The headline is the net value after charging the plan for its spend on false alerts.
// The method is shown on the page, so the number can be checked rather than taken on trust.
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import type { ValueCase } from '../api/types'
import { Badge, Card, ErrorNote, Kpi, Loading } from '../components/ui'
import { compactMoney, hours, money, optionLabel, shortTime } from '../lib/format'
import { useAsync } from '../state/useAsync'

const CHART_HEIGHT = 240

export function TrackRecord() {
  const record = useAsync(api.trackRecord, [])
  const [onlyDiffer, setOnlyDiffer] = useState(true)
  if (record.error) return <ErrorNote message={record.error} />
  if (!record.data) return <Loading label="Scoring every alert against what happened" />
  const { summary: s, cases, method } = record.data
  const differing = cases.filter((c) => c.recommended_kind !== c.baseline_kind)
  const shown = onlyDiffer ? differing : cases
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Track record</h1>
        <p className="text-sm text-slate-500">
          {s.alerts} alerts from {shortTime(s.period.first ?? '')} to {shortTime(s.period.last ?? '')}: {s.real_failures} were
          followed by the failure, {s.false_alerts} were false. The copilot's plan differed from the site's own choice {s.plans_that_differ} times.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <Kpi label="Net value" value={compactMoney(s.net_usd)} tone="good" hint="After charging false-alert spend" />
        <Kpi label="Downtime avoided" value={hours(s.hours_saved)} tone="good" hint="On real failures" />
        <Kpi label="Saved on failures" value={compactMoney(s.usd_saved_on_failures)} hint="Extra spend plus lost contribution" />
        <Kpi label="Spent on false alerts" value={money(s.usd_spent_on_false_alerts)} tone="warn" hint="Charged against the value" />
      </div>
      <Card title="Where the plan changed the outcome">
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <BarChart data={differing.map((c) => ({ name: `${c.asset_id} ${shortTime(c.raised_at).split(' ').slice(0, 2).join(' ')}`, saved: c.usd_saved }))}
            margin={{ top: 5, right: 10, bottom: 0, left: 10 }}>
            <CartesianGrid stroke="#eef2f7" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
            <YAxis tickFormatter={(v: number) => compactMoney(v)} tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
            <Tooltip formatter={(v) => money(Number(v))} />
            <Bar dataKey="saved" name="Saved" radius={[4, 4, 0, 0]}>
              {differing.map((c) => <Cell key={c.alert_id} fill={c.usd_saved >= 0 ? '#059669' : '#e11d48'} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>
      <Card title="Every alert, scored" action={
        <label className="flex items-center gap-2 text-xs text-slate-600">
          <input type="checkbox" checked={onlyDiffer} onChange={(e) => setOnlyDiffer(e.target.checked)} />Only where the plan differed
        </label>}>
        <CaseTable cases={shown} />
      </Card>
      <Card title="Method">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">{method.map((m) => <li key={m}>{m}</li>)}</ul>
      </Card>
    </div>
  )
}

function CaseTable({ cases }: { cases: ValueCase[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
          {['Alert', 'Raised', 'Outcome', 'Copilot', 'Site alone', 'Down (copilot / alone)', 'Saved'].map((h) =>
            <th key={h} className="whitespace-nowrap px-3 py-2 font-medium">{h}</th>)}
        </tr></thead>
        <tbody>{cases.map((c) => (
          <tr key={c.alert_id} className="border-b border-slate-100">
            <td className="whitespace-nowrap px-3 py-2 font-medium">{c.asset_id}</td>
            <td className="whitespace-nowrap px-3 py-2 tabular-nums">{shortTime(c.raised_at)}</td>
            <td className="whitespace-nowrap px-3 py-2">{c.failed_at ? <Badge tone="danger">failed {shortTime(c.failed_at)}</Badge> : <Badge>no failure</Badge>}</td>
            <td className="whitespace-nowrap px-3 py-2">{optionLabel(c.recommended_kind)}</td>
            <td className="whitespace-nowrap px-3 py-2 text-slate-600">{optionLabel(c.baseline_kind)}</td>
            <td className="whitespace-nowrap px-3 py-2 tabular-nums">{hours(c.copilot.lost_hours)} / {hours(c.baseline.lost_hours)}</td>
            <td className={`whitespace-nowrap px-3 py-2 font-semibold tabular-nums ${c.usd_saved < 0 ? 'text-rose-700' : c.usd_saved > 0 ? 'text-emerald-700' : ''}`}>{money(c.usd_saved)}</td>
          </tr>))}
        </tbody>
      </table>
    </div>
  )
}
