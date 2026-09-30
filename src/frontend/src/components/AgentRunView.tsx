// Runs one copilot question and shows the agent working: each tool call appears as it happens, then the answer.
// The answer carries a verified badge when every number in it came from a tool result, and the full results stay
// one click away. Provider errors, such as a quota limit, are shown as they are, never as an empty answer.
import { CheckCircle2, ChevronRight, CircleAlert, Loader2, Wrench } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import { streamAgent } from '../api/agentStream'
import type { AgentDoneEvent, AgentEvent } from '../api/types'

interface ToolStep {
  name: string
  args: unknown
  result?: unknown
}

const TOOL_LABELS: Record<string, string> = {
  list_open_alerts: 'Listed open alerts',
  analyse_alert_impact: 'Analysed impact',
  get_sensor_evidence: 'Read sensor evidence',
  get_supplier_record: 'Checked supplier record',
  oee_summary: 'Computed OEE',
  failures: 'Read failure history',
  work_order_history: 'Read work orders',
  propose_action_plan: 'Drafted a proposal',
}

export function AgentRunView({ question, asOf, onFinished }:
  { question: string; asOf: string; onFinished?: (done: AgentDoneEvent | null) => void }) {
  const [steps, setSteps] = useState<ToolStep[]>([])
  const [done, setDone] = useState<AgentDoneEvent | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const started = useRef(false)
  useEffect(() => {
    if (started.current) return
    started.current = true
    let final: AgentDoneEvent | null = null
    const handle = (event: AgentEvent) => {
      if (event.type === 'tool_call') setSteps((s) => [...s, { name: event.name, args: event.payload }])
      else if (event.type === 'tool_result') setSteps((s) => attachResult(s, event.name, event.payload))
      else if (event.type === 'done') { final = event; setDone(event) }
    }
    streamAgent(question, asOf, handle).catch((e: Error) => setFailure(e.message)).finally(() => onFinished?.(final))
  }, [question, asOf, onFinished])
  return (
    <div className="space-y-4">
      <ol className="space-y-2">
        {steps.map((step, index) => <StepRow key={index} step={step} />)}
        {!done && !failure && (
          <li className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />{steps.length ? 'Reasoning over the results' : 'Gemini is planning its first step'}
          </li>
        )}
      </ol>
      {failure && <ErrorLine text={failure} />}
      {done && <Answer done={done} />}
    </div>
  )
}

function attachResult(steps: ToolStep[], name: string, result: unknown): ToolStep[] {
  const index = steps.findIndex((s) => s.name === name && s.result === undefined)
  if (index < 0) return steps
  return steps.map((s, i) => (i === index ? { ...s, result } : s))
}

function StepRow({ step }: { step: ToolStep }) {
  const [open, setOpen] = useState(false)
  const args = JSON.stringify(step.args)
  return (
    <li className="rounded-lg border border-slate-200 bg-white">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm">
        {step.result === undefined ? <Loader2 className="h-4 w-4 animate-spin text-brand-600" /> : <Wrench className="h-4 w-4 text-brand-600" />}
        <span className="shrink-0 font-medium">{TOOL_LABELS[step.name] ?? step.name}</span>
        <code className="min-w-0 flex-1 truncate font-mono text-xs text-slate-500">{step.name}({args === '{}' ? '' : args})</code>
        <ChevronRight className={`h-4 w-4 shrink-0 text-slate-400 transition ${open ? 'rotate-90' : ''}`} />
      </button>
      {open && step.result !== undefined && (
        <pre className="max-h-72 overflow-auto border-t border-slate-100 bg-slate-50 px-3 py-2 font-mono text-xs text-slate-700">
          {JSON.stringify(step.result, null, 2)}
        </pre>
      )}
    </li>
  )
}

export function Answer({ done }: { done: AgentDoneEvent }) {
  if (done.error) return <ErrorLine text={`The model could not answer: ${done.error}`} />
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="text-sm leading-relaxed [overflow-wrap:anywhere] [&_code]:rounded [&_code]:bg-slate-100 [&_code]:px-1 [&_code]:font-mono [&_code]:text-xs [&_h1]:mt-3 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:mt-3 [&_h2]:text-base [&_h2]:font-semibold [&_h3]:mt-3 [&_h3]:font-semibold [&_hr]:my-3 [&_hr]:border-slate-200 [&_li]:my-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-2 [&_strong]:font-semibold [&_strong]:text-ink [&_ul]:list-disc [&_ul]:pl-5">
        <Markdown>{done.answer}</Markdown>
      </div>
      <div className={`mt-4 flex items-center gap-2 rounded-lg px-3 py-2 text-xs ${done.verified ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'}`}>
        {done.verified ? <CheckCircle2 className="h-4 w-4" /> : <CircleAlert className="h-4 w-4" />}
        {done.verified
          ? 'Verified: every number in this answer comes from a tool result.'
          : `Not verified: ${done.unexplained_numbers.join(', ')} not found in any tool result.`}
        <span className="ml-auto text-slate-500">{done.tools_used.length} tool calls · {done.seconds.toFixed(1)} s · {done.model}</span>
      </div>
    </div>
  )
}

function ErrorLine({ text }: { text: string }) {
  return <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">{text}</div>
}
