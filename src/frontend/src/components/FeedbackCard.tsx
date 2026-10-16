// Operator verdicts on an alert: mark it as false with a reason, confirm it, undo it, and see earlier verdicts.
// A verdict on an earlier alert of the same machine and failure mode shows as a caution, never as a hidden alert,
// because the same machine can still fail; nothing is recorded until a person confirms, and Enter never submits.
import { Flag, Loader2, Undo2 } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client'
import type { AlertFeedback } from '../api/types'
import { shortTime } from '../lib/format'
import { confirmPrompt } from '../lib/verdict'
import { useAsync } from '../state/useAsync'
import { Badge, Callout, Card, ErrorNote } from './ui'

const REASON_LIMIT = 300
const BUTTON = 'inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50'

interface FeedbackCardProps { alertId: string; asOf: string; assetId: string; failureMode: string; onChange: () => void }

export function FeedbackCard({ alertId, asOf, assetId, failureMode, onChange }: FeedbackCardProps) {
  const [version, setVersion] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const view = useAsync(() => api.feedback(alertId, asOf), [alertId, asOf, version])
  const run = async (action: () => Promise<unknown>): Promise<boolean> => {
    setBusy(true); setError(null)
    try { await action(); setVersion((v) => v + 1); onChange(); return true }
    catch (e) { setError((e as Error).message); return false } finally { setBusy(false) }
  }
  const own = view.data?.own ?? []
  return (
    <Card title={<span className="inline-flex items-center gap-2"><Flag className="h-4 w-4" />Operator verdict</span>}>
      {view.data?.caution && <div className="mb-3"><Callout>{view.data.caution}</Callout></div>}
      {own.length > 0 ? (
        <ul className="space-y-2">{own.map((f) => (
          <VerdictRow key={f.marked_at + f.reason} feedback={f} busy={busy}
            onUndo={() => run(() => api.withdrawFeedback(alertId, asOf))} />
        ))}</ul>
      ) : (
        <VerdictForm busy={busy} prompt={confirmPrompt(assetId, failureMode)}
          onConfirm={(reason) => run(() => api.markFalse(alertId, reason, asOf))} />
      )}
      {error && <div className="mt-3"><ErrorNote message={error} /></div>}
    </Card>
  )
}

function VerdictForm({ busy, prompt, onConfirm }:
  { busy: boolean; prompt: string; onConfirm: (reason: string) => Promise<boolean> }) {
  const [reason, setReason] = useState('')
  const [confirming, setConfirming] = useState(false)
  const confirm = async () => {
    if (await onConfirm(reason)) { setReason(''); setConfirming(false) }
  }
  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500">
        If this alert is false, say why. Later alerts on this machine and failure mode will show your note and ask
        for an inspection first. They are never hidden, because the same machine can still fail.
      </p>
      <div className="flex gap-2">
        <input value={reason} onChange={(e) => setReason(e.target.value)} maxLength={REASON_LIMIT}
          placeholder="For example: gear teeth intact on inspection; the oil needed flushing"
          className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none" />
        <button type="button" disabled={busy || confirming || !reason.trim()} onClick={() => setConfirming(true)} className={BUTTON}>
          <Flag className="h-4 w-4" />Mark as false alert
        </button>
      </div>
      {confirming && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
          <span className="min-w-0 flex-1">{prompt}</span>
          <button type="button" disabled={busy || !reason.trim()} onClick={confirm} className={BUTTON}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Flag className="h-4 w-4" />}Confirm
          </button>
          <button type="button" disabled={busy} onClick={() => setConfirming(false)} className={BUTTON}>Cancel</button>
        </div>
      )}
    </div>
  )
}

function VerdictRow({ feedback: f, busy, onUndo }: { feedback: AlertFeedback; busy: boolean; onUndo: () => void }) {
  return (
    <li className="flex items-start gap-2 rounded-lg border border-slate-200 p-3 text-sm">
      <Badge tone="warn">marked false</Badge>
      <span className="min-w-0 flex-1">{f.reason}</span>
      <span className="shrink-0 text-xs text-slate-500">{shortTime(f.marked_at)}</span>
      <button type="button" disabled={busy} onClick={onUndo}
        className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-900 disabled:opacity-50">
        <Undo2 className="h-3.5 w-3.5" />Undo
      </button>
    </li>
  )
}
