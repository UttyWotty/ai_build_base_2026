// The app shell: a navigation rail, and a top bar with the scenario picker, the demo clock, and the model in use.
// Every page renders inside it, so the demo clock is always visible and one click away from change.
// The model chip reads the backend's engine status, so it always shows what really answers.
import { Bot, ClipboardCheck, Factory, Inbox, Network, Radio, TrendingUp } from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { api } from '../api/client'
import { shortTime } from '../lib/format'
import { useClock } from '../state/clockContext'
import { useAsync } from '../state/useAsync'

const NAV = [
  { to: '/live', label: 'Live', icon: Radio },
  { to: '/', label: 'Control room', icon: Factory },
  { to: '/copilot', label: 'Copilot', icon: Bot },
  { to: '/inbox', label: 'Supplier inbox', icon: Inbox },
  { to: '/approvals', label: 'Approvals', icon: ClipboardCheck },
  { to: '/track-record', label: 'Track record', icon: TrendingUp },
  { to: '/how-it-works', label: 'How it works', icon: Network },
]

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full">
      <nav className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2 px-5 py-5">
          <img src="/favicon.svg" alt="" className="h-8 w-8" />
          <div>
            <div className="text-sm font-bold tracking-tight">OSI</div>
            <div className="text-[11px] text-slate-500">Opsight Intelligence</div>
          </div>
        </div>
        <div className="flex flex-col gap-1 px-3">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'}
              className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${
                isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100'}`}>
              <Icon className="h-4 w-4" />{label}
            </NavLink>
          ))}
        </div>
        <div className="mt-auto px-5 py-4 text-[11px] leading-relaxed text-slate-400">
          Synthetic data from seeded generators. Gemini via the Agent Development Kit.
        </div>
      </nav>
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-y-auto px-8 py-6">{children}</main>
      </div>
    </div>
  )
}

function TopBar() {
  const { asOf, setAsOf, scenarios } = useClock()
  const engine = useAsync(api.engineStatus, [])
  const active = scenarios.find((s) => s.as_of === asOf)
  return (
    <header className="flex items-center gap-4 border-b border-slate-200 bg-white px-8 py-3">
      <div className="flex rounded-lg bg-slate-100 p-1">
        {scenarios.map((s) => (
          <button key={s.id} onClick={() => setAsOf(s.as_of)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${s.as_of === asOf ? 'bg-white shadow-sm text-ink' : 'text-slate-600'}`}>
            {s.label}
          </button>
        ))}
      </div>
      <input type="datetime-local" value={asOf} onChange={(e) => e.target.value && setAsOf(e.target.value)}
        className="rounded-lg border border-slate-200 px-2 py-1.5 text-sm text-slate-700" aria-label="Demo clock" />
      <div className="min-w-0 flex-1 truncate text-sm text-slate-500">{active?.story ?? `Replaying ${shortTime(asOf)} UTC`}</div>
      <div className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600">
        {engine.data ? `${engine.data.model} · ADK` : 'Connecting to backend'}
      </div>
    </header>
  )
}
