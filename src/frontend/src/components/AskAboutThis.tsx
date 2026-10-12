// An in-place conversation with the copilot about one part of the app, such as an alert's field inspection.
// Each turn streams like any agent run; follow-up questions carry the topic and the recent turns.
// Suggested questions start the conversation in one click; turns stay until the alert or the clock changes.
import { MessageSquare, Send } from 'lucide-react'
import { useCallback, useState } from 'react'
import type { AgentDoneEvent } from '../api/types'
import { composeQuestion, type Turn } from '../lib/conversation'
import { AgentRunView } from './AgentRunView'

interface AskedTurn {
  id: number
  shown: string
  sent: string
  answer?: string
}

export function AskAboutThis({ topic, asOf, placeholder, suggestions }:
  { topic: string; asOf: string; placeholder: string; suggestions: string[] }) {
  const [turns, setTurns] = useState<AskedTurn[]>([])
  const [draft, setDraft] = useState('')
  const busy = turns.some((t) => t.answer === undefined)
  const ask = (question: string) => {
    if (!question.trim() || busy) return
    const history: Turn[] = turns.map((t) => ({ question: t.shown, answer: t.answer ?? '' }))
    setTurns((all) => [...all, { id: Date.now(), shown: question.trim(), sent: composeQuestion(topic, history, question) }])
    setDraft('')
  }
  const finish = useCallback((id: number, done: AgentDoneEvent | null) => {
    setTurns((all) => all.map((t) => (t.id === id ? { ...t, answer: done && !done.error ? done.answer : '' } : t)))
  }, [])
  return (
    <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
      <p className="inline-flex items-center gap-2 text-sm font-medium"><MessageSquare className="h-4 w-4 text-brand-600" />Ask about this</p>
      {turns.map((t) => (
        <div key={t.id} className="space-y-2">
          <p className="ml-auto w-fit max-w-[85%] rounded-lg bg-brand-50 px-3 py-2 text-sm">{t.shown}</p>
          <AgentRunView question={t.sent} asOf={asOf} onFinished={(done) => finish(t.id, done)} />
        </div>
      ))}
      {turns.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((q) => (
            <button key={q} onClick={() => ask(q)} className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 hover:border-brand-500">{q}</button>
          ))}
        </div>
      )}
      <form onSubmit={(e) => { e.preventDefault(); ask(draft) }} className="flex gap-2">
        <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={busy ? 'Gemini is answering' : placeholder} disabled={busy}
          className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none disabled:bg-slate-50" />
        <button disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-3 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">
          <Send className="h-4 w-4" />Ask
        </button>
      </form>
    </div>
  )
}
