// The copilot page: ask Gemini anything about the plant and its supply at the demo clock, and watch it work.
// Suggested questions cover the demo story; each run streams its tool calls and ends with a verified answer.
// Runs stack newest first and stay until the page reloads.
import { Send } from 'lucide-react'
import { useState } from 'react'
import type { AgentMode } from '../api/types'
import { AgentRunView } from '../components/AgentRunView'
import { Card } from '../components/ui'
import { shortTime } from '../lib/format'
import { useClock } from '../state/clockContext'

const SUGGESTIONS = [
  'Which alerts need attention right now, and what do you recommend?',
  'Two alerts need the same spare. Who gets it, and how is the other one covered?',
  'How reliable has supplier V10001 been lately?',
  'What was the OEE of line US1-L2 in the last 30 days?',
]

interface Run { id: number; question: string; asOf: string; mode: AgentMode }

export function Copilot() {
  const { asOf } = useClock()
  const [runs, setRuns] = useState<Run[]>([])
  const [draft, setDraft] = useState('')
  const [mode, setMode] = useState<AgentMode>('single')
  const ask = (question: string) => {
    if (!question.trim()) return
    setRuns((r) => [{ id: Date.now(), question: question.trim(), asOf, mode }, ...r])
    setDraft('')
  }
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Ask the copilot</h1>
        <p className="text-sm text-slate-500">
          Gemini answers from governed tools only, as of {shortTime(asOf)} UTC. Every number is checked against the tool results.
        </p>
      </div>
      <div className="flex rounded-lg bg-slate-100 p-1 text-sm w-fit">
        {(['single', 'team'] as AgentMode[]).map((m) => (
          <button key={m} onClick={() => setMode(m)} className={`rounded-md px-3 py-1 ${m === mode ? 'bg-white shadow-sm' : 'text-slate-600'}`}>
            {m === 'single' ? 'One agent' : 'Operations team (4 agents)'}
          </button>
        ))}
      </div>
      <form onSubmit={(e) => { e.preventDefault(); ask(draft) }} className="flex gap-2">
        <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Ask about alerts, spares, suppliers, customers, or OEE"
          className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm shadow-sm focus:border-brand-500 focus:outline-none" />
        <button className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-medium text-white hover:bg-brand-700">
          <Send className="h-4 w-4" />Ask
        </button>
      </form>
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((q) => (
          <button key={q} onClick={() => ask(q)} className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 hover:border-brand-500">
            {q}
          </button>
        ))}
      </div>
      {runs.map((run) => (
        <Card key={run.id} title={run.question} action={<span className="text-xs text-slate-400">as of {shortTime(run.asOf)}</span>}>
          <AgentRunView question={run.question} asOf={run.asOf} mode={run.mode} />
        </Card>
      ))}
    </div>
  )
}
