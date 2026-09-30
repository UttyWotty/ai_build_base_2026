// Types of the JSON the FastAPI backend returns, mirroring copilot/core/agent_views.py and the API endpoints.
// Keeping them in one file makes a backend change show up as a compile error here, not a blank screen.
// Numbers arrive already rounded the way the interface should show them.

export interface Scenario {
  id: string
  label: string
  as_of: string
  story: string
}

export interface ScenarioList {
  default_as_of: string
  scenarios: Scenario[]
}

export interface EngineStatus {
  ready: boolean
  model: string
  provider: string
}

export interface OrderAtRisk {
  so_line_id: string
  customer: string
  part_id: string
  quantity: number
  committed: string
}

export interface RecoveryOption {
  kind: string
  source: string
  ready_at: string
  planned_repair: boolean
  extra_cost_usd: number
  downtime_hours: number
  lost_contribution_usd: number
  total_cost_usd: number
  worst_case_downtime_hours: number | null
  customer_lines_at_risk: number
  customer_value_at_risk_usd: number
  orders_at_risk: OrderAtRisk[]
  recommended_by_rules: boolean
}

export interface AlertRow {
  alert_id: string
  asset_id: string
  line_id: string
  failure_mode: string
  raised_at: string
  repair_deadline: string
  priority: string
}

export interface OverviewAlert extends AlertRow {
  recommended: RecoveryOption
  conflict: string | null
  downtime_avoided_hours: number
  cost_avoided_usd: number
}

export interface Headline {
  open_alerts: number
  alerts_in_spare_conflict: number
  downtime_avoided_hours: number
  cost_avoided_usd: number
}

export interface Overview {
  as_of: string
  headline: Headline
  alerts: OverviewAlert[]
}

export interface OpenOrder {
  po_id: string
  quantity: number
  promised: string
  expected: string
}

export interface SparePosition {
  site_id: string
  on_hand: number
  open_orders: OpenOrder[]
  alerts_queued_for_this_spare: string[]
}

export interface Impact {
  alert: AlertRow
  as_of: string
  repair_hours: number
  planned_slot_available: boolean
  line: { line_id: string; units_per_hour: number; contribution_usd_per_unit: number }
  options: RecoveryOption[]
  assumptions: string[]
  conflict: string | null
  baseline: RecoveryOption
  spare?: { spare_part_id: string; label: string; unit_cost_usd: number; local: SparePosition; sister_sites: SparePosition[] }
  supplier?: {
    supplier_id: string
    name: string
    on_time_percent: number | null
    expected_days_late: number
    window: string
    window_days: number
    governed_metric: string
    sql_fingerprint: string
  }
  past_alerts_of_this_mode?: { count: number; fastest_failure_hours: number; median_failure_hours: number }
}

export interface SensorSeries {
  sensor: string
  label: string
  unit: string
  normal_range: [number, number]
  grain: string
  values: { period: string; mean: number }[]
}

export interface Evidence {
  alert_id: string
  asset_id: string
  failure_mode: string
  pf_interval_days: number
  recommended_action: string
  sensors: SensorSeries[]
}

export interface Proposal {
  proposal_id: string
  alert_id: string
  asset_id: string
  created_at: string
  option_kind: string
  option_source: string
  ready_at: string
  extra_cost_usd: number
  downtime_hours: number
  lost_contribution_usd: number
  orders_at_risk: string[]
  work_order_note: string
  customer_note: string
  status: 'pending' | 'approved' | 'rejected'
}

export type AgentStepType = 'tool_call' | 'tool_result' | 'text' | 'error'

export interface AgentStepEvent {
  type: AgentStepType
  name: string
  payload: unknown
}

export interface AgentDoneEvent {
  type: 'done'
  answer: string
  verified: boolean
  error: string
  unexplained_numbers: string[]
  seconds: number
  model: string
  tools_used: string[]
}

export type AgentEvent = AgentStepEvent | AgentDoneEvent
