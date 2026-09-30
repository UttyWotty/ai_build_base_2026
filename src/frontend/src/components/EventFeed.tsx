// The plant event feed: newest first, colour-coded by severity, with events that just arrived highlighted.
// Alerts that opened their own work order are marked, because those are what the autopilot triages.
// The feed only ever shows events up to the demo clock.
import { AlertTriangle, CheckCircle2, CircleDot, PackageCheck, Wrench } from 'lucide-react'
import type { PlantEvent } from '../api/types'
import { shortTime } from '../lib/format'
import { eventKey } from '../lib/live'

const STYLE = {
  critical: { icon: Wrench, tone: 'text-rose-600', bar: 'border-l-rose-500' },
  warning: { icon: AlertTriangle, tone: 'text-amber-600', bar: 'border-l-amber-500' },
  good: { icon: CheckCircle2, tone: 'text-emerald-600', bar: 'border-l-emerald-500' },
  info: { icon: CircleDot, tone: 'text-slate-400', bar: 'border-l-slate-300' },
}

export function EventFeed({ events, fresh }: { events: PlantEvent[]; fresh: Set<string> }) {
  if (events.length === 0) return <p className="p-4 text-sm text-slate-500">Nothing has happened yet in this window.</p>
  return (
    <ol className="space-y-1.5">
      {events.map((event) => {
        const style = STYLE[event.severity]
        const Icon = event.kind === 'spare_received' ? PackageCheck : style.icon
        const isFresh = fresh.has(eventKey(event))
        return (
          <li key={eventKey(event)} className={`flex gap-3 rounded-lg border border-l-4 border-slate-200 bg-white px-3 py-2 text-sm transition-colors duration-700 ${style.bar} ${isFresh ? 'bg-brand-50' : ''}`}>
            <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${style.tone}`} />
            <div className="min-w-0 flex-1">
              <div className="[overflow-wrap:anywhere]">{event.title}</div>
              <div className="text-xs text-slate-500">{shortTime(event.at)} · {event.site_id}</div>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
