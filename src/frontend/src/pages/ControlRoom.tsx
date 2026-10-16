// The control room: headline numbers for the demo clock, the open alerts, and the selected alert in full.
// The first alert is shown until another is picked, and again whenever the clock moves to a moment without it.
// Everything comes from the overview and impact endpoints, so it matches what the agent sees.
import { useState } from 'react'
import { api } from '../api/client'
import { AlertDetail } from '../components/AlertDetail'
import { AlertList } from '../components/AlertList'
import { ErrorNote, Kpi, Loading } from '../components/ui'
import { compactMoney, hours } from '../lib/format'
import { useClock } from '../state/clockContext'
import { useAsync } from '../state/useAsync'

export function ControlRoom() {
  const { asOf } = useClock()
  const [version, setVersion] = useState(0)
  const overview = useAsync(() => api.overview(asOf), [asOf, version])
  const [chosen, setSelected] = useState<string | null>(null)
  const alerts = overview.data?.alerts ?? []
  const selected = alerts.some((a) => a.alert_id === chosen) ? chosen : alerts[0]?.alert_id ?? null
  if (overview.error) return <ErrorNote message={overview.error} />
  if (!overview.data) return <Loading label="Loading the plant, the supply network, and the bridge" />
  const h = overview.data.headline
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <Kpi label="Open alerts" value={String(h.open_alerts)} hint="Waiting for a repair right now" />
        <Kpi label="Spare conflicts" value={String(h.alerts_in_spare_conflict)} tone={h.alerts_in_spare_conflict ? 'warn' : 'neutral'}
          hint="Alerts competing for the same part" />
        <Kpi label="Downtime avoided" value={hours(h.downtime_avoided_hours)} tone="good" hint="Plan versus each site acting alone" />
        <Kpi label="Cost avoided" value={compactMoney(h.cost_avoided_usd)} tone="good" hint="Extra spend plus lost contribution" />
      </div>
      {alerts.length === 0 ? (
        <p className="text-sm text-slate-500">No alerts are waiting for a repair at this moment.</p>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[300px_1fr]">
          <AlertList alerts={alerts} selected={selected} onSelect={setSelected} />
          {selected && <div className="min-w-0"><AlertDetail key={selected} alertId={selected} asOf={asOf}
            onVerdict={() => setVersion((v) => v + 1)} /></div>}
        </div>
      )}
    </div>
  )
}
