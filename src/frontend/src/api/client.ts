// Thin client for the FastAPI backend: one function per endpoint, each returning typed JSON.
// Paths are relative, so the Vite proxy (development) and Firebase Hosting rewrites (production) both work.
// A non-2xx response throws ApiError with the backend's detail message, which the pages show as is.
import type { EngineStatus, Evidence, Impact, Overview, Proposal, ScenarioList, TrackRecord } from './types'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) throw await toError(response)
  return (await response.json()) as T
}

export async function toError(response: Response): Promise<ApiError> {
  const body = await response.json().catch(() => ({}))
  const detail = typeof body?.detail === 'string' ? body.detail : response.statusText
  return new ApiError(response.status, detail)
}

const clock = (asOf: string): string => `as_of=${encodeURIComponent(asOf)}`

export const api = {
  engineStatus: (): Promise<EngineStatus> => getJson('/api/engine-status'),
  scenarios: (): Promise<ScenarioList> => getJson('/api/scenarios'),
  overview: (asOf: string): Promise<Overview> => getJson(`/api/overview?${clock(asOf)}`),
  impact: (alertId: string, asOf: string): Promise<Impact> =>
    getJson(`/api/alerts/${encodeURIComponent(alertId)}/impact?${clock(asOf)}`),
  evidence: (alertId: string, asOf: string): Promise<Evidence> =>
    getJson(`/api/alerts/${encodeURIComponent(alertId)}/evidence?${clock(asOf)}`),
  trackRecord: (): Promise<TrackRecord> => getJson('/api/value'),
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
