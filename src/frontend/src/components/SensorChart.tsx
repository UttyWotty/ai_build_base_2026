// Plots each symptom sensor's daily mean against its normal range, so the reason for the alert is visible at a glance.
// The shaded band is the normal range from the plant catalog; points above it are what the model reacted to.
// One small chart per sensor keeps units separate.
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { SensorSeries } from '../api/types'
import { shortDate } from '../lib/format'

const CHART_HEIGHT = 170

export function SensorChart({ series }: { series: SensorSeries }) {
  const [low, high] = series.normal_range
  const rows = series.values.map((v) => ({ day: shortDate(v.period), mean: v.mean, band: [low, high] }))
  const above = series.values.some((v) => v.mean > high)
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-sm">
        <span className="font-medium">{series.label}</span>
        <span className="text-xs text-slate-500">normal {low}–{high} {series.unit.replace(/_/g, ' ')}</span>
      </div>
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <ComposedChart data={rows} margin={{ top: 5, right: 10, bottom: 0, left: -10 }}>
          <CartesianGrid stroke="#eef2f7" vertical={false} />
          <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
          <Tooltip formatter={(value) => (Array.isArray(value) ? `${value[0]}–${value[1]}` : value)} />
          <Area dataKey="band" fill="#d1fae5" stroke="none" isAnimationActive={false} name="Normal range" />
          <Line dataKey="mean" animationDuration={500} stroke={above ? '#e11d48' : '#1a56db'} strokeWidth={2} dot={{ r: 3 }} name="Daily mean" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
