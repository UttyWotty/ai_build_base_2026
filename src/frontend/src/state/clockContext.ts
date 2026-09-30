// The demo clock's context object and the hook pages use to read it.
// It lives apart from the provider component so hot reload keeps working during development.
// Using the hook outside the provider is a programming error and fails loudly.
import { createContext, useContext } from 'react'
import type { Scenario } from '../api/types'

export interface ClockState {
  asOf: string
  setAsOf: (value: string) => void
  scenarios: Scenario[]
}

export const ClockContext = createContext<ClockState | null>(null)

export function useClock(): ClockState {
  const state = useContext(ClockContext)
  if (!state) throw new Error('useClock must be used inside ClockProvider')
  return state
}
