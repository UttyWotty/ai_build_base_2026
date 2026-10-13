// Live operations: the plant replayed as it happens. The clock runs, events stream into the feed, and with the
// autopilot on, the Gemini agent triages every new alert the moment it arrives and leaves a proposal for approval.
// It is the page that shows the copilot working on its own, with a person still approving every action.
import { Pause, Play, SkipForward } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { AgentDoneEvent, PlantEvent } from '../api/types'
import { AutopilotPanel } from '../components/AutopilotPanel'
import { EventFeed } from '../components/EventFeed'
import { Card, ErrorNote, Kpi } from '../components/ui'
import { addHours, longClock } from '../lib/clockMath'
import { compactMoney, hours } from '../lib/format'
import { afterTriages, eventKey, plural, type Triage } from '../lib/live'
import { useAction } from '../state/useAction'
import { useClock } from '../state/clockContext'
import { useAsync } from '../state/useAsync'
import { useLiveClock } from '../state/useLiveClock'

const SPEEDS = [1, 3, 6]
const STARTS = [
  { label: 'Bearing week at US1', at: '2026-07-24T12:00' },
  { label: 'Pump wear at DE1', at: '2026-08-18T12:00' },
]
const FEED_LOOKBACK_HOURS = -24
// Errors that would repeat on every alert: stop the autopilot rather than fail each triage.
const STOPPING_KINDS = new Set(['quota', 'auth', 'limit'])

export function Live() {
  const { asOf, setAsOf } = useClock()
  const [running, setRunning] = useState(false)
  const [speed, setSpeed] = useState(SPEEDS[0])
  const [autopilot, setAutopilot] = useState(true)
  // On by default: a proposal is decided before the clock passes the failure it is about, even at the fastest speed.
  const [waitForApproval, setWaitForApproval] = useState(true)
  const [held, setHeld] = useState(false)
  const [windowStart, setWindowStart] = useState(() => addHours(asOf, FEED_LOOKBACK_HOURS))
  const [triages, setTriages] = useState<Triage[]>([])
  const [decisions, setDecisions] = useState(0)
  const [stoppedReason, setStoppedReason] = useState<string | null>(null)
  const resumeAfterTriage = useRef(false)
  const stop = useCallback(() => setRunning(false), [])
  const run = (next: boolean) => { setHeld(false); setRunning(next) }
  useLiveClock(running, speed, stop)
  // Each jump starts a new epoch, even a jump back to the same start for a second take. A response carries the epoch
  // it was asked in, so the new window is never diffed against the old one and its existing alerts are not re-triaged.
  const [jumps, setJumps] = useState(0)
  const epoch = `${windowStart}#${jumps}`
  const feed = useAsync(async () => ({ epoch, events: await api.events(windowStart, asOf) }), [epoch, asOf, decisions])
  const events = feed.data?.epoch === epoch ? feed.data.events : null
  const overview = useAsync(() => api.overview(asOf), [asOf, decisions])
  const pending = useAsync(async () => (await api.proposals()).filter((p) => p.status === 'pending'), [asOf, triages, decisions])
  const action = useAction()
  const decide = (id: string, status: 'approved' | 'rejected') =>
    action.run(async () => { await api.setProposalStatus(id, status); setDecisions((n) => n + 1) })
  const fresh = useFreshKeys(events?.map(eventKey) ?? null, epoch)
  useAutopilotTrigger(events, epoch, autopilot, running, setTriages, () => {
    resumeAfterTriage.current = true
    setRunning(false)
  })
  const finishTriage = useCallback((alertId: string, result: AgentDoneEvent | null) => {
    setTriages((all) => all.map((t) => (t.event.alert_id === alertId ? { ...t, done: true, result } : t)))
    if (result && STOPPING_KINDS.has(result.error_kind)) {
      resumeAfterTriage.current = false
      setAutopilot(false)
      setStoppedReason(result.error_message)
    }
  }, [])
  // The clock moves on only when every triage of the batch has finished, not when the first one does; with the wait
  // on, a batch that left a proposal holds the clock until the person presses Run.
  useEffect(() => {
    if (!resumeAfterTriage.current) return
    const next = afterTriages(triages, waitForApproval)
    if (next === 'wait') return
    resumeAfterTriage.current = false
    if (next === 'hold') setHeld(true)
    else setRunning(true)
  }, [triages, waitForApproval])
  const jumpTo = (at: string) => {
    resumeAfterTriage.current = false
    setHeld(false); setRunning(false); setTriages([]); setAsOf(at); setWindowStart(addHours(at, FEED_LOOKBACK_HOURS)); setJumps((n) => n + 1)
  }
  const h = overview.data?.headline
  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center gap-4">
          <button onClick={() => run(!running)} className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
            {running ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}{running ? 'Pause' : 'Run'}
          </button>
          <button onClick={() => setAsOf(addHours(asOf, 1))} className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"><SkipForward className="h-4 w-4" />1 h</button>
          <div className="flex rounded-lg bg-slate-100 p-1 text-sm">
            {SPEEDS.map((s) => <button key={s} onClick={() => setSpeed(s)} className={`rounded-md px-2.5 py-1 ${s === speed ? 'bg-white shadow-sm' : 'text-slate-600'}`}>{s} h/s</button>)}
          </div>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={autopilot} onChange={(e) => { setAutopilot(e.target.checked); if (e.target.checked) setStoppedReason(null) }} />Autopilot</label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={waitForApproval} onChange={(e) => setWaitForApproval(e.target.checked)} />Wait for approval</label>
          <div className="ml-auto text-right">
            <div className="text-lg font-semibold tabular-nums">{longClock(asOf)}</div>
            <div className="flex gap-2 text-xs text-slate-500">{STARTS.map((s) => <button key={s.at} onClick={() => jumpTo(s.at)} className="underline-offset-2 hover:underline">{s.label}</button>)}</div>
          </div>
        </div>
        {held && (
          <p className="mt-3 text-sm text-amber-700">
            Paused for a decision: approve or reject the proposal, then press Run. The clock waits so the plan is decided
            before the moment it is about.
          </p>
        )}
      </Card>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_1.2fr]">
        <Card title="Plant events" action={<span className="text-xs text-slate-400">since {longClock(windowStart)}</span>}>
          <div className="max-h-[640px] overflow-y-auto pr-1"><EventFeed events={events ?? []} fresh={fresh} /></div>
        </Card>
        <div className="min-w-0 space-y-4">
          <div className="grid grid-cols-2 gap-3 2xl:grid-cols-4">
            <Kpi label="Open alerts" value={String(h?.open_alerts ?? '–')} />
            <Kpi label="Spare conflicts" value={String(h?.alerts_in_spare_conflict ?? '–')} tone={h?.alerts_in_spare_conflict ? 'warn' : 'neutral'} />
            <Kpi label="Downtime avoided" value={h ? hours(h.downtime_avoided_hours) : '–'} tone="good" />
            <Kpi label="Cost avoided" value={h ? compactMoney(h.cost_avoided_usd) : '–'} tone="good" />
          </div>
          {action.error && <ErrorNote message={action.error} />}
          <AutopilotPanel triages={triages} enabled={autopilot} onFinished={finishTriage} pending={pending.data ?? []} onDecide={decide}
            busy={action.busy} stoppedReason={stoppedReason} />
          <Link to="/approvals" className="block rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm hover:border-brand-500">
            <span className="font-semibold">{plural(pending.data?.length ?? 0, 'proposal')}</span> waiting for approval →
          </Link>
        </div>
      </div>
    </div>
  )
}

// Keys that appeared since the last response; the first response of each window only seeds what is already known.
function useFreshKeys(keys: string[] | null, epoch: string): Set<string> {
  const seen = useRef<{ epoch: string; keys: Set<string> } | null>(null)
  const [fresh, setFresh] = useState<Set<string>>(new Set())
  const signature = keys?.join('\n') ?? null
  useEffect(() => {
    if (keys === null) return
    if (seen.current?.epoch !== epoch) { seen.current = { epoch, keys: new Set(keys) }; setFresh(new Set()); return }
    const known = seen.current.keys
    const added = keys.filter((k) => !known.has(k))
    added.forEach((k) => known.add(k))
    if (added.length) setFresh(new Set(added))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, epoch])
  return fresh
}

// Alerts already in a window when it is first shown are known; only alerts that arrive afterwards are triaged.
function useAutopilotTrigger(events: PlantEvent[] | null, epoch: string, enabled: boolean, running: boolean,
                             setTriages: Dispatch<SetStateAction<Triage[]>>, pause: () => void): void {
  const known = useRef<{ epoch: string; ids: Set<string> } | null>(null)
  useEffect(() => {
    if (events === null) return
    const alerts = events.filter((e) => e.kind === 'alert' && e.alert_id)
    if (known.current?.epoch !== epoch) { known.current = { epoch, ids: new Set(alerts.map((e) => e.alert_id!)) }; return }
    const ids = known.current.ids
    const arrived = alerts.filter((e) => !ids.has(e.alert_id!)).reverse()
    arrived.forEach((e) => ids.add(e.alert_id!))
    if (!enabled || !running || arrived.length === 0) return
    setTriages((all) => [...all, ...arrived.map((event) => ({ event, done: false }))])
    pause()
  }, [events, epoch, enabled, running, setTriages, pause])
}
