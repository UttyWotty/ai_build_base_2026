// How it works: the sense, reason, act loop, the architecture from data to decision, the guardrails, and Google Cloud.
// It is the page judges read to see what is real; every claim points at something the other pages show.
// The diagram is plain markup, so it scales and needs no image files.
import { ArrowRight, Bot, Database, Eye, ShieldCheck, UserCheck } from 'lucide-react'
import type { ReactNode } from 'react'
import { Card } from '../components/ui'

const LOOP = [
  { icon: Eye, title: 'Sense', text: 'A gradient-boosted model scores every asset from its sensors. On the last four months it caught 27 of 41 failures at 0.16 false alerts per asset-month, with a median warning of 86 hours.' },
  { icon: Bot, title: 'Reason', text: "A team of Gemini agents on Google's Agent Development Kit investigates with governed tools: a maintenance planner, a procurement lead, and a customer service lead work in parallel, then an operations lead weighs their briefs." },
  { icon: UserCheck, title: 'Act', text: 'It proposes the work order, the parts action, and the customer note. A person approves or rejects each one.' },
]

const GUARDRAILS = [
  ['No invented numbers', 'Every number in an answer is checked against the tool results before it is marked verified.'],
  ['No SQL from the model', 'Supplier metrics compile from governed definitions; each answer shows the SQL fingerprint.'],
  ['No peeking at the future', 'Every tool answers as of the demo clock; outcomes count only once they are in the past.'],
  ['No silent actions', 'The agent creates proposals; only a person can approve them.'],
]

const PLATFORM = [
  ['Reasoning', 'Gemini on Vertex AI, through the Agent Development Kit'],
  ['Service', 'One Cloud Run service: FastAPI for the API and the agent stream, serving the React app'],
  ['Identity', 'A service account limited to Vertex AI; no API key is deployed'],
  ['Data', 'DuckDB over Parquet inside the service, generated from seeds'],
]

function Box({ icon, title, sub, accent = false }: { icon: ReactNode; title: string; sub: string; accent?: boolean }) {
  return (
    <div className={`rounded-xl border px-4 py-3 ${accent ? 'border-brand-500 bg-brand-50' : 'border-slate-200 bg-white'}`}>
      <div className="flex items-center gap-2 text-sm font-semibold">{icon}{title}</div>
      <div className="mt-0.5 text-xs text-slate-500">{sub}</div>
    </div>
  )
}

const arrow = <ArrowRight className="h-4 w-4 shrink-0 self-center text-slate-400" />

export function HowItWorks() {
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {LOOP.map(({ icon: Icon, title, text }) => (
          <Card key={title}><div className="flex items-center gap-2 font-semibold"><Icon className="h-5 w-5 text-brand-600" />{title}</div>
            <p className="mt-2 text-sm text-slate-600">{text}</p></Card>
        ))}
      </div>
      <Card title="Architecture">
        <div className="grid grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr_auto_1fr] items-center gap-2">
          <div className="space-y-2">
            <Box icon={<Database className="h-4 w-4" />} title="Plant" sub="sensors, MES, CMMS" />
            <Box icon={<Database className="h-4 w-4" />} title="Supply network" sub="ERP, TMS, suppliers" />
          </div>
          {arrow}
          <div className="space-y-2">
            <Box icon={<Eye className="h-4 w-4" />} title="Failure prediction" sub="gradient boosting" />
            <Box icon={<Database className="h-4 w-4" />} title="Governed bridge" sub="sites, spares, suppliers, lines" />
          </div>
          {arrow}
          <Box icon={<ShieldCheck className="h-4 w-4" />} title="Impact analysis" sub="point in time, priced options" />
          {arrow}
          <Box icon={<Bot className="h-4 w-4" />} title="Gemini agent team" sub="ADK: 3 specialists in parallel, then a lead" accent />
          {arrow}
          <Box icon={<UserCheck className="h-4 w-4" />} title="Person approves" sub="proposals only" />
        </div>
      </Card>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card title="Guardrails">
          <dl className="space-y-3 text-sm">{GUARDRAILS.map(([t, d]) => <div key={t}><dt className="font-medium">{t}</dt><dd className="text-slate-600">{d}</dd></div>)}</dl>
        </Card>
        <Card title="On Google Cloud">
          <dl className="space-y-3 text-sm">{PLATFORM.map(([t, d]) => <div key={t}><dt className="font-medium">{t}</dt><dd className="text-slate-600">{d}</dd></div>)}</dl>
        </Card>
      </div>
      <p className="text-xs text-slate-400">All data is synthetic and generated from seeds; no real plant, supplier, or customer data is used.</p>
    </div>
  )
}
