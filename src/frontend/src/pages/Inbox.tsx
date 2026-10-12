// The supplier inbox: Gemini reads suppliers' messages (text or PDF) into delivery updates, and a delayed order's new
// date flows straight into the impact analysis. Sample messages make the demo one click; any message can be pasted.
// Updates count from the moment each message was received, so the demo clock decides which ones are known.
import { FileText, Loader2, Mail, Paperclip, RotateCcw } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client'
import type { SampleMessage, SupplierUpdate } from '../api/types'
import { Badge, Card, ErrorNote } from '../components/ui'
import { toUpload } from '../lib/files'
import { shortTime } from '../lib/format'
import { useClock } from '../state/clockContext'
import { useAsync } from '../state/useAsync'

const CHANGE_TONE = { delay: 'danger', earlier: 'good', on_time: 'good', cancelled: 'danger', no_delivery_change: 'neutral' } as const

export function Inbox() {
  const { asOf } = useClock()
  const [version, setVersion] = useState(0)
  const samples = useAsync(api.fieldSamples, [])
  const updates = useAsync(() => api.supplierUpdates(asOf), [asOf, version])
  const refresh = () => setVersion((v) => v + 1)
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Supplier inbox</h1>
          <p className="text-sm text-slate-500">Gemini reads suppliers' messages into delivery updates. A new date replaces the expected arrival of the open order, and every analysis sees it from the moment the message arrived.</p>
        </div>
        <button onClick={async () => { await api.resetField(); refresh() }} className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">
          <RotateCcw className="h-4 w-4" />Reset
        </button>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title={<span className="inline-flex items-center gap-2"><Mail className="h-4 w-4" />Messages</span>}>
          <div className="space-y-3">
            {(samples.data?.messages ?? []).map((m) => <MessageCard key={m.name} message={m} onRead={refresh} />)}
            <PasteBox onRead={refresh} />
          </div>
        </Card>
        <Card title="Delivery updates known now">
          {updates.error && <ErrorNote message={updates.error} />}
          {(updates.data ?? []).length === 0 ? <p className="text-sm text-slate-500">None yet at {shortTime(asOf)}. Read a message to add one.</p> : (
            <ul className="space-y-3">{(updates.data ?? []).map((u, i) => <UpdateRow key={i} update={u} />)}</ul>
          )}
        </Card>
      </div>
    </div>
  )
}

function MessageCard({ message, onRead }: { message: SampleMessage; onRead: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const read = async () => {
    setBusy(true); setError(null)
    try { await api.readSupplierMessage(message.text, message.received_at); onRead() } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <div className="text-sm font-medium">{message.subject}</div>
      <div className="text-xs text-slate-500">{message.sender} · {shortTime(message.received_at)}</div>
      <details className="mt-2 text-xs text-slate-600"><summary className="cursor-pointer">Show message</summary><pre className="mt-2 whitespace-pre-wrap font-sans">{message.text}</pre></details>
      <button onClick={read} disabled={busy} className="mt-2 inline-flex items-center gap-1.5 rounded-md bg-brand-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-60">
        {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />}Read with Gemini
      </button>
      {error && <div className="mt-2"><ErrorNote message={error} /></div>}
    </div>
  )
}

function PasteBox({ onRead }: { onRead: () => void }) {
  const { asOf } = useClock()
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const read = async () => {
    setBusy(true); setError(null)
    try {
      await api.readSupplierMessage(text, asOf, file ? [await toUpload(file)] : [])
      setText(''); setFile(null); onRead()
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  return (
    <div className="rounded-lg border border-dashed border-slate-300 p-3">
      <div className="text-sm font-medium">Your own message</div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} placeholder="Paste a supplier email, or attach a PDF"
        className="mt-2 w-full rounded-md border border-slate-200 p-2 text-sm" />
      <div className="mt-2 flex items-center gap-2">
        <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium hover:bg-slate-50">
          <Paperclip className="h-3.5 w-3.5" />Attach PDF or image
          <input type="file" accept="application/pdf,image/*" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </label>
        {file && <span className="min-w-0 truncate text-xs text-slate-600">{file.name}</span>}
        <button onClick={read} disabled={busy || (!text && !file)} className="ml-auto rounded-md bg-brand-600 px-2.5 py-1 text-xs font-medium text-white disabled:opacity-50">Read with Gemini</button>
      </div>
      {error && <div className="mt-2"><ErrorNote message={error} /></div>}
    </div>
  )
}

function UpdateRow({ update: u }: { update: SupplierUpdate }) {
  return (
    <li className="rounded-lg border border-slate-200 p-3 text-sm">
      <div className="flex items-center gap-2">
        <span className="font-medium">{u.supplier_name}</span>
        <Badge tone={CHANGE_TONE[u.change as keyof typeof CHANGE_TONE] ?? 'neutral'}>{u.change.replace(/_/g, ' ')}</Badge>
        <span className="ml-auto text-xs text-slate-500">received {shortTime(u.received_at)}</span>
      </div>
      {u.order_reference && <div className="mt-1 font-mono text-xs">{u.order_reference}{u.new_delivery_at ? ` → new delivery ${shortTime(u.new_delivery_at)}` : ''}</div>}
      <div className="mt-1 text-xs text-slate-600">{u.reason}</div>
    </li>
  )
}
