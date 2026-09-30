// The autopilot: every alert that opens a work order while the clock runs is triaged by the Gemini agent at once.
// The run streams into the panel and ends with a proposal waiting for approval; finished runs stay listed below.
// The clock pauses while the agent works, so its analysis is for the moment the alert arrived.
import { Bot } from 'lucide-react'
import { hours, money, optionLabel, shortTime } from '../lib/format'
import { type Triage, triageQuestion } from '../lib/live'
import { Check, X } from 'lucide-react'
import type { AgentDoneEvent, Proposal } from '../api/types'
import { AgentRunView, Answer } from './AgentRunView'
import { Badge, Card } from './ui'

export function AutopilotPanel({ triages, enabled, onFinished, pending, onDecide, stoppedReason }:
  { triages: Triage[]; enabled: boolean; onFinished: (alertId: string, result: AgentDoneEvent | null) => void;
    pending: Proposal[]; onDecide: (id: string, status: 'approved' | 'rejected') => void; stoppedReason: string | null }) {
  const active = triages.find((t) => !t.done)
  const finished = triages.filter((t) => t.done)
  return (
    <Card title={<span className="inline-flex items-center gap-2"><Bot className="h-4 w-4 text-brand-600" />Autopilot</span>}
      action={<Badge tone={enabled ? 'good' : 'neutral'}>{enabled ? 'on' : 'off'}</Badge>}>
      {stoppedReason && (
        <p className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Autopilot stopped and the clock paused: {stoppedReason} The replay itself keeps working; switch the autopilot back on when the model is available.
        </p>
      )}
      {!active && finished.length === 0 && (
        <p className="text-sm text-slate-500">
          {enabled ? 'Watching for new alerts. Each one is triaged by Gemini as soon as it arrives.' : 'Switch the autopilot on to triage new alerts automatically.'}
        </p>
      )}
      {active && active.event.alert_id && (
        <div className="space-y-2">
          <div className="text-sm font-medium">Triaging {active.event.subject}, raised {shortTime(active.event.at)}</div>
          <AgentRunView key={active.event.alert_id} question={triageQuestion(active.event.alert_id)} asOf={active.event.at.replace(' ', 'T')}
            onFinished={(result) => onFinished(active.event.alert_id ?? '', result)} mode="team" />
        </div>
      )}
      {!active && finished.length > 0 && finished[finished.length - 1].result && (
        <div className="space-y-2">
          <div className="text-sm font-medium">Latest: {finished[finished.length - 1].event.subject}, raised {shortTime(finished[finished.length - 1].event.at)}</div>
          <Answer done={finished[finished.length - 1].result!} />
          {pending.filter((p) => p.alert_id === finished[finished.length - 1].event.alert_id).map((p) => (
            <DecisionBar key={p.proposal_id} proposal={p} onDecide={onDecide} />
          ))}
        </div>
      )}
      {finished.length > 0 && (
        <ul className="mt-4 space-y-1 border-t border-slate-100 pt-3 text-xs text-slate-600">
          {finished.map((t) => <li key={t.event.alert_id}>Triaged {t.event.subject} ({shortTime(t.event.at)}): {t.result?.error ? 'not triaged, the model could not answer' : 'proposal sent for approval'}</li>)}
        </ul>
      )}
    </Card>
  )
}

function DecisionBar({ proposal: p, onDecide }: { proposal: Proposal; onDecide: (id: string, s: 'approved' | 'rejected') => void }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-brand-100 bg-brand-50 px-3 py-2 text-sm">
      <span className="font-medium">Proposal: {optionLabel(p.option_kind)} from {p.option_source}</span>
      <span className="text-slate-600">{money(p.extra_cost_usd)} extra, {hours(p.downtime_hours)} down</span>
      <span className="ml-auto flex gap-2">
        <button onClick={() => onDecide(p.proposal_id, 'approved')} className="inline-flex items-center gap-1 rounded-md bg-emerald-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-emerald-700"><Check className="h-3.5 w-3.5" />Approve</button>
        <button onClick={() => onDecide(p.proposal_id, 'rejected')} className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700"><X className="h-3.5 w-3.5" />Reject</button>
      </span>
    </div>
  )
}
