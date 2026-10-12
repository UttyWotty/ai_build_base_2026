// Runs one user action at a time, such as approving a proposal or resetting the demo, and keeps its busy and error state.
// While an action runs, buttons that use it are disabled, so a double click never sends the request twice.
// A failure is kept as a message for the page to show instead of an unhandled rejection that leaves nothing on screen.
import { useCallback, useState } from 'react'

export interface ActionState {
  busy: boolean
  error: string | null
  run: (action: () => Promise<unknown>) => Promise<void>
}

export function useAction(): ActionState {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const run = useCallback(async (action: () => Promise<unknown>) => {
    setBusy(true)
    setError(null)
    try { await action() } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }, [])
  return { busy, error, run }
}
