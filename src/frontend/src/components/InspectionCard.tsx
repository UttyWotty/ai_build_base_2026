// Field inspection for one alert: a technician's photo, read by Gemini vision against the predicted failure mode.
// Sample photos for the asset are one click away; any photo can be uploaded. Findings stay listed with their time.
// A finding that contradicts the prediction is shown as clearly as one that confirms it, and the copilot answers
// follow-up questions about the inspection in place.
import { Camera, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client'
import type { InspectionFinding, SamplePhoto } from '../api/types'
import { toUpload } from '../lib/files'
import { shortTime } from '../lib/format'
import { useAsync } from '../state/useAsync'
import { AskAboutThis } from './AskAboutThis'
import { Badge, Card, ErrorNote } from './ui'

const ASK_SUGGESTIONS = [
  'Does the inspection confirm the alert, and what should we do?',
  'What should the technician check next?',
  'Is it safe to wait for the open order?',
]

const CONDITION_TONE = { healthy: 'good', early_wear: 'warn', severe_wear: 'danger', failed: 'danger', unclear: 'neutral' } as const

export function InspectionCard({ alertId, assetId, asOf }: { alertId: string; assetId: string; asOf: string }) {
  const [version, setVersion] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const findings = useAsync(() => api.inspections(alertId, asOf), [alertId, asOf, version])
  const samples = useAsync(api.fieldSamples, [])
  const photos = (samples.data?.photos ?? []).filter((p) => p.asset_id === assetId)
  const send = async (blob: Blob, mime?: string) => {
    setBusy(true); setError(null)
    try { await api.inspect(alertId, await toUpload(blob, mime), asOf); setVersion((v) => v + 1) }
    catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const sendSample = async (photo: SamplePhoto) => send(await (await fetch(`/api/field/samples/photos/${photo.name}`)).blob(), photo.mime_type)
  return (
    <Card title={<span className="inline-flex items-center gap-2"><Camera className="h-4 w-4" />Field inspection</span>}>
      <div className="flex flex-wrap items-center gap-2">
        <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium hover:bg-slate-50">
          Upload photo<input type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && send(e.target.files[0])} />
        </label>
        {photos.map((p) => (
          <button key={p.name} onClick={() => sendSample(p)} className="rounded-md border border-slate-200 px-2.5 py-1 text-xs hover:border-brand-500">Sample: {p.name}</button>
        ))}
        {busy && <span className="inline-flex items-center gap-1 text-xs text-slate-500"><Loader2 className="h-3.5 w-3.5 animate-spin" />Gemini is looking at the photo</span>}
      </div>
      {error && <div className="mt-3"><ErrorNote message={error} /></div>}
      <ul className="mt-3 space-y-3">
        {(findings.data ?? []).map((f, i) => <FindingRow key={i} finding={f} />)}
        {findings.data?.length === 0 && !busy && <li className="text-sm text-slate-500">No inspection yet. A photo of the part lets Gemini confirm or question the prediction before anyone spends money.</li>}
      </ul>
      <AskAboutThis key={`${alertId}-${asOf}`} topic={askTopic(alertId, assetId)} asOf={asOf}
        placeholder="Ask about this inspection" suggestions={ASK_SUGGESTIONS} />
    </Card>
  )
}

function askTopic(alertId: string, assetId: string): string {
  return `Alert ${alertId} on asset ${assetId} and its field inspection photos. Use get_field_reports for the inspection `
    + 'findings, and get_sensor_evidence or analyse_alert_impact when the question needs them.'
}

function FindingRow({ finding: f }: { finding: InspectionFinding }) {
  return (
    <li className="rounded-lg border border-slate-200 p-3 text-sm">
      <div className="flex items-center gap-2">
        <Badge tone={CONDITION_TONE[f.condition as keyof typeof CONDITION_TONE] ?? 'neutral'}>{f.condition.replace(/_/g, ' ')}</Badge>
        <Badge tone={f.matches_predicted_failure ? 'danger' : 'good'}>{f.matches_predicted_failure ? 'confirms the prediction' : 'does not confirm it'}</Badge>
        <span className="ml-auto text-xs text-slate-500">confidence {Math.round(f.confidence * 100)}% · {shortTime(f.received_at)}</span>
      </div>
      <ul className="mt-2 list-disc pl-5 text-xs text-slate-600">{f.observations.map((o) => <li key={o}>{o}</li>)}</ul>
      <p className="mt-2 text-xs"><span className="font-medium">Advice:</span> {f.advice}</p>
    </li>
  )
}
