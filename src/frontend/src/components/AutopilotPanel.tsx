// The autopilot: every alert that opens a work order while the clock runs is triaged by the Gemini agent at once.
// The run streams into the panel and ends with a proposal waiting for approval; finished runs stay listed below.
// The clock pauses while the agent works, so its analysis is for the moment the alert arrived.
import { Bot } from 'lucide-react'
import { shortTime } from '../lib/format'
import { type Triage, triageQuestion } from '../lib/live'
import type { AgentDoneEvent } from '../api/types'
import { AgentRunView, Answer } from './AgentRunView'
import { Badge, Card } from './ui'

export function AutopilotPanel({ triages, enabled, onFinished }:
  { triages: Triage[]; enabled: boolean; onFinished: (alertId: string, result: AgentDoneEvent | null) => void }) {
  const active = triages.find((t) => !t.done)
  const finished = triages.filter((t) => t.done)
  return (
    <Card title={<span className="inline-flex items-center gap-2"><Bot className="h-4 w-4 text-brand-600" />Autopilot</span>}
      action={<Badge tone={enabled ? 'good' : 'neutral'}>{enabled ? 'on' : 'off'}</Badge>}>
      {!active && finished.length === 0 && (
        <p className="text-sm text-slate-500">
          {enabled ? 'Watching for new alerts. Each one is triaged by Gemini as soon as it arrives.' : 'Switch the autopilot on to triage new alerts automatically.'}
        </p>
      )}
      {active && active.event.alert_id && (
        <div className="space-y-2">
          <div className="text-sm font-medium">Triaging {active.event.subject}, raised {shortTime(active.event.at)}</div>
          <AgentRunView key={active.event.alert_id} question={triageQuestion(active.event.alert_id)} asOf={active.event.at.replace(' ', 'T')}
            onFinished={(result) => onFinished(active.event.alert_id ?? '', result)} />
        </div>
      )}
      {!active && finished.length > 0 && finished[finished.length - 1].result && (
        <div className="space-y-2">
          <div className="text-sm font-medium">Latest: {finished[finished.length - 1].event.subject}, raised {shortTime(finished[finished.length - 1].event.at)}</div>
          <Answer done={finished[finished.length - 1].result!} />
        </div>
      )}
      {finished.length > 0 && (
        <ul className="mt-4 space-y-1 border-t border-slate-100 pt-3 text-xs text-slate-600">
          {finished.map((t) => <li key={t.event.alert_id}>Triaged {t.event.subject} ({shortTime(t.event.at)}): {t.result?.error ? 'the model could not answer' : 'proposal sent for approval'}</li>)}
        </ul>
      )}
    </Card>
  )
}
