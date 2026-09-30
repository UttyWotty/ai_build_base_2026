// The demo clock: the moment every page and the agent treat as now, shared through React context.
// It starts at the backend's default scenario and changes when a scenario or a custom time is picked.
// Pages read asOf from here so they always refetch for the same moment.
import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import type { Scenario } from '../api/types'
import { ClockContext } from './clockContext'

const FALLBACK_AS_OF = '2026-07-25T02:00'

export function ClockProvider({ children }: { children: ReactNode }) {
  const [asOf, setAsOf] = useState(FALLBACK_AS_OF)
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  useEffect(() => {
    api.scenarios().then((list) => {
      setScenarios(list.scenarios)
      setAsOf(list.default_as_of)
    }).catch(() => setScenarios([]))
  }, [])
  return <ClockContext.Provider value={{ asOf, setAsOf, scenarios }}>{children}</ClockContext.Provider>
}
