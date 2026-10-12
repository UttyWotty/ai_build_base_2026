// Operator verdicts on an alert: mark it as false with a reason, and see what operators said about earlier alerts.
// A verdict on an earlier alert of the same machine and failure mode shows as a caution, never as a hidden alert,
// because the same machine can still fail; the copilot reads the same verdicts through its field-report tool.
import { Flag, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client'
import type { AlertFeedback } from '../api/types'
import { shortTime } from '../lib/format'
import { useAsync } from '../state/useAsync'
import { Badge, Callout, Card, ErrorNote } from './ui'

const REASON_LIMIT = 300

export function FeedbackCard({ alertId, asOf }: { alertId: string; asOf: string }) {
  const [version, setVersion] = useState(0)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const view = useAsync(() => api.feedback(alertId, asOf), [alertId, asOf, version])
  const submit = async () => {
    setBusy(true); setError(null)
    try { await api.markFalse(alertId, reason, asOf); setReason(''); setVersion((v) => v + 1) }
    catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const own = view.data?.own ?? []
  return (
    <Card title={<span className="inline-flex items-center gap-2"><Flag className="h-4 w-4" />Operator verdict</span>}>
      {view.data?.caution && <div className="mb-3"><Callout>{view.data.caution}</Callout></div>}
      {own.length > 0 ? (
        <ul className="space-y-2">{own.map((f) => <VerdictRow key={f.marked_at + f.reason} feedback={f} />)}</ul>
      ) : (
        <form onSubmit={(e) => { e.preventDefault(); submit() }} className="space-y-2">
          <p className="text-xs text-slate-500">
            If this alert is false, say why. Later alerts on this machine and failure mode will show your note and ask
            for an inspection first. They are never hidden, because the same machine can still fail.
          </p>
          <div className="flex gap-2">
            <input value={reason} onChange={(e) => setReason(e.target.value)} maxLength={REASON_LIMIT}
              placeholder="For example: gear teeth intact on inspection; the oil needed flushing"
              className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none" />
            <button disabled={busy || !reason.trim()}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 text-sm font-medium hover:bg-slate-50 disabled:opacity-50">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Flag className="h-4 w-4" />}Mark as false alert
            </button>
          </div>
        </form>
      )}
      {error && <div className="mt-3"><ErrorNote message={error} /></div>}
    </Card>
  )
}

function VerdictRow({ feedback: f }: { feedback: AlertFeedback }) {
  return (
    <li className="flex items-start gap-2 rounded-lg border border-slate-200 p-3 text-sm">
      <Badge tone="warn">marked false</Badge>
      <span className="min-w-0 flex-1">{f.reason}</span>
      <span className="shrink-0 text-xs text-slate-500">{shortTime(f.marked_at)}</span>
    </li>
  )
}
