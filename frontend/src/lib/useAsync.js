import { useCallback, useEffect, useRef, useState } from 'react'

/** Minimal data-fetching hook: { data, loading, error, reload }. */
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const fnRef = useRef(fn)
  fnRef.current = fn

  const reload = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const data = await fnRef.current()
      setState({ data, loading: false, error: null })
      return data
    } catch (error) {
      setState({ data: null, loading: false, error })
      return null
    }
  }, [])

  const setData = useCallback((data) => setState((s) => ({ ...s, data })), [])

  useEffect(() => { reload() }, deps) // eslint-disable-line react-hooks/exhaustive-deps
  return { ...state, setData, reload }
}
