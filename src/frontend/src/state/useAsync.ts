// A small data-loading hook: runs an async loader when its inputs change and exposes data, error, and loading.
// Stale responses are ignored, so switching scenarios quickly never shows the previous moment's numbers.
// reload() reruns the loader, for example after a proposal changes status.
import { useCallback, useEffect, useRef, useState } from 'react'

export interface AsyncState<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
}

export function useAsync<T>(loader: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  const request = useRef(0)
  useEffect(() => {
    const id = ++request.current
    setLoading(true)
    setError(null)
    loader()
      .then((value) => { if (id === request.current) setData(value) })
      .catch((reason: unknown) => { if (id === request.current) setError(String((reason as Error)?.message ?? reason)) })
      .finally(() => { if (id === request.current) setLoading(false) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])
  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { data, error, loading, reload }
}
