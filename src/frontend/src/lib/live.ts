// Shared pieces of live mode that are not components: the event identity key, the triage record, and the question
// the autopilot asks the agent for each new alert. Kept apart from the components so hot reload keeps working.
// The question asks for a proposal, never an action, because only a person approves.
import type { AgentDoneEvent, PlantEvent } from '../api/types'

export interface Triage {
  event: PlantEvent
  done: boolean
  result?: AgentDoneEvent | null
}

export const eventKey = (e: PlantEvent): string => `${e.at}|${e.kind}|${e.title}`

export const triageQuestion = (alertId: string): string =>
  `A new alert was just raised: ${alertId}. Triage it now: check its impact and any spare conflict, choose the best ` +
  'option, create the proposal for approval, and summarise in three short sentences.'

export const plural = (count: number, word: string): string => `${count} ${word}${count === 1 ? '' : 's'}`

export const AGENT_LABELS: Record<string, string> = {
  operations_copilot: 'Copilot',
  maintenance_planner: 'Maintenance planner',
  procurement_lead: 'Procurement lead',
  customer_lead: 'Customer service lead',
  operations_lead: 'Operations lead',
}

export const agentLabel = (author: string): string => AGENT_LABELS[author] ?? author
