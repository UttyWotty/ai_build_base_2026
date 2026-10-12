// Thin client for the FastAPI backend: one function per endpoint, each returning typed JSON.
// Paths are relative, so the Vite proxy (development) and Firebase Hosting rewrites (production) both work.
// A non-2xx response throws ApiError with the backend's detail message, which the pages show as is.
import type {
  AlertFeedback, EngineStatus, Evidence, FeedbackView, FieldSamples, Impact, InspectionFinding, Outcome, Overview, PlantEvent, Proposal, ScenarioList,
  SupplierUpdate, TrackRecord,
} from './types'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) })
  if (!response.ok) throw await toError(response)
  return (await response.json()) as T
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) throw await toError(response)
  return (await response.json()) as T
}

export async function toError(response: Response): Promise<ApiError> {
  const body: unknown = await response.json().catch(() => null)
  return new ApiError(response.status, errorDetail(body, response.status, response.statusText))
}

// The backend's message when it sent one; FastAPI's validation errors (422) carry a list of issues instead of a string.
// HTTP/2 responses have no status text, so the status code is the last resort and an error is never shown empty.
export function errorDetail(body: unknown, status: number, statusText: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((d) => (d as { msg?: unknown })?.msg).filter((m): m is string => typeof m === 'string')
    if (messages.length) return `The request was not accepted: ${messages.join('; ')}`
  }
  return `The server answered ${status}${statusText ? ` ${statusText}` : ''}. Try again in a moment.`
}

const clock = (asOf: string): string => `as_of=${encodeURIComponent(asOf)}`

export interface Upload { mime_type: string; data_base64: string }

export const api = {
  engineStatus: (): Promise<EngineStatus> => getJson('/api/engine-status'),
  scenarios: (): Promise<ScenarioList> => getJson('/api/scenarios'),
  overview: (asOf: string): Promise<Overview> => getJson(`/api/overview?${clock(asOf)}`),
  impact: (alertId: string, asOf: string): Promise<Impact> =>
    getJson(`/api/alerts/${encodeURIComponent(alertId)}/impact?${clock(asOf)}`),
  evidence: (alertId: string, asOf: string): Promise<Evidence> =>
    getJson(`/api/alerts/${encodeURIComponent(alertId)}/evidence?${clock(asOf)}`),
  trackRecord: (): Promise<TrackRecord> => getJson('/api/value'),
  events: async (start: string, end: string): Promise<PlantEvent[]> =>
    (await getJson<{ events: PlantEvent[] }>(`/api/events?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`)).events,
  outcomes: async (asOf: string): Promise<Outcome[]> =>
    (await getJson<{ outcomes: Outcome[] }>(`/api/proposals/outcomes?${clock(asOf)}`)).outcomes,
  resetProposals: async (): Promise<void> => {
    const response = await fetch('/api/proposals/reset', { method: 'POST' })
    if (!response.ok) throw await toError(response)
  },
  fieldSamples: (): Promise<FieldSamples> => getJson('/api/field/samples'),
  readSupplierMessage: (text: string, receivedAt: string, attachments: Upload[] = []): Promise<SupplierUpdate> =>
    postJson('/api/field/supplier-message', { text, received_at: receivedAt, attachments }),
  supplierUpdates: async (asOf: string): Promise<SupplierUpdate[]> =>
    (await getJson<{ updates: SupplierUpdate[] }>(`/api/field/supplier-updates?${clock(asOf)}`)).updates,
  inspect: (alertId: string, upload: Upload, asOf: string): Promise<InspectionFinding> =>
    postJson(`/api/alerts/${encodeURIComponent(alertId)}/inspection`, { ...upload, as_of: asOf }),
  inspections: async (alertId: string, asOf: string): Promise<InspectionFinding[]> =>
    (await getJson<{ inspections: InspectionFinding[] }>(`/api/alerts/${encodeURIComponent(alertId)}/inspections?${clock(asOf)}`)).inspections,
  feedback: (alertId: string, asOf: string): Promise<FeedbackView> =>
    getJson(`/api/alerts/${encodeURIComponent(alertId)}/feedback?${clock(asOf)}`),
  markFalse: (alertId: string, reason: string, asOf: string): Promise<AlertFeedback> =>
    postJson(`/api/alerts/${encodeURIComponent(alertId)}/feedback`, { reason, as_of: asOf }),
  resetField: async (): Promise<void> => { await postJson('/api/field/reset', {}) },
  proposals: async (): Promise<Proposal[]> => (await getJson<{ proposals: Proposal[] }>('/api/proposals')).proposals,
  setProposalStatus: async (proposalId: string, status: 'approved' | 'rejected'): Promise<Proposal> => {
    const response = await fetch(`/api/proposals/${encodeURIComponent(proposalId)}/status`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    if (!response.ok) throw await toError(response)
    return (await response.json()) as Proposal
  },
}
