// The approval queue: every plan the copilot proposed, with its numbers, notes, and a person's decision.
// Approving or rejecting records the decision only; nothing is ordered or moved by this app.
// Pending proposals come first so the next decision is always at the top.
import { Check, RotateCcw, X } from 'lucide-react'
import { api } from '../api/client'
import type { Outcome, Proposal } from '../api/types'
import { OutcomeLine } from '../components/OutcomeLine'
import { Badge, Card, ErrorNote, Loading } from '../components/ui'
import { hours, money, optionLabel, shortTime } from '../lib/format'
import { useClock } from '../state/clockContext'
import { useAsync } from '../state/useAsync'

const STATUS_TONE = { pending: 'warn', approved: 'good', rejected: 'neutral' } as const

export function Approvals() {
  const { asOf } = useClock()
  const proposals = useAsync(api.proposals, [])
  const outcomes = useAsync(() => api.outcomes(asOf), [asOf, proposals.data])
  if (proposals.error) return <ErrorNote message={proposals.error} />
  if (!proposals.data) return <Loading />
  const ordered = [...proposals.data].sort((a, b) => Number(b.status === 'pending') - Number(a.status === 'pending'))
  const decide = async (id: string, status: 'approved' | 'rejected') => {
    await api.setProposalStatus(id, status)
    proposals.reload()
  }
  const reset = async () => {
    await api.resetProposals()
    proposals.reload()
  }
  const byProposal = new Map((outcomes.data ?? []).map((o) => [o.proposal_id, o]))
  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Approvals</h1>
          <p className="text-sm text-slate-500">The copilot proposes; a person decides. Approved plans change stock and queues from their moment on, and their outcome appears once the clock passes it.</p>
        </div>
        <button onClick={reset} className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">
          <RotateCcw className="h-4 w-4" />Reset demo
        </button>
      </div>
      {ordered.length === 0 && <p className="text-sm text-slate-500">No proposals yet. Draft one from the control room.</p>}
      {ordered.map((p) => <ProposalCard key={p.proposal_id} proposal={p} outcome={byProposal.get(p.proposal_id)} onDecide={decide} />)}
    </div>
  )
}

function ProposalCard({ proposal: p, outcome, onDecide }:
  { proposal: Proposal; outcome: Outcome | undefined; onDecide: (id: string, s: 'approved' | 'rejected') => void }) {
  return (
    <Card title={<span className="inline-flex items-center gap-2">{p.asset_id}: {optionLabel(p.option_kind)} from {p.option_source}
      <Badge tone={STATUS_TONE[p.status]}>{p.status}</Badge></span>}
      action={<span className="text-xs text-slate-400">{p.proposal_id}</span>}>
      <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
        <div><div className="text-xs text-slate-500">Spare ready</div>{shortTime(p.ready_at)}</div>
        <div><div className="text-xs text-slate-500">Extra cost</div>{money(p.extra_cost_usd)}</div>
        <div><div className="text-xs text-slate-500">Downtime</div>{hours(p.downtime_hours)}</div>
        <div><div className="text-xs text-slate-500">Customer lines at risk</div>{p.orders_at_risk.length}</div>
      </div>
      <div className="mt-4 space-y-2 text-sm">
        <p><span className="font-medium">Work order:</span> {p.work_order_note || '–'}</p>
        <p><span className="font-medium">Customer note:</span> {p.customer_note || '–'}</p>
        {p.status === 'approved' && <OutcomeLine outcome={outcome} />}
      </div>
      {p.status === 'pending' && (
        <div className="mt-4 flex gap-2">
          <button onClick={() => onDecide(p.proposal_id, 'approved')}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700">
            <Check className="h-4 w-4" />Approve
          </button>
          <button onClick={() => onDecide(p.proposal_id, 'rejected')}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
            <X className="h-4 w-4" />Reject
          </button>
        </div>
      )}
    </Card>
  )
}
