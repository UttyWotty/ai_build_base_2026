// Drives live mode: while running, the demo clock advances by a set number of hours every second.
// Pausing stops the timer; the clock itself lives in the shared clock context, so every page follows it.
// A cap stops the clock at the end of the data rather than running into an empty future.
import { useEffect } from 'react'
import { addHours, isAfter } from '../lib/clockMath'
import { useClock } from './clockContext'

const TICK_MS = 1000
export const DATA_END = '2026-09-27T23:00'

export function useLiveClock(running: boolean, hoursPerTick: number, onEnd: () => void): void {
  const { asOf, setAsOf } = useClock()
  useEffect(() => {
    if (!running) return
    const timer = window.setTimeout(() => {
      const next = addHours(asOf, hoursPerTick)
      if (isAfter(next, DATA_END)) onEnd()
      else setAsOf(next)
    }, TICK_MS)
    return () => window.clearTimeout(timer)
  }, [running, hoursPerTick, asOf, setAsOf, onEnd])
}
