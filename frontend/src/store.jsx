import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api } from './api'

const StoreContext = createContext(null)

export function StoreProvider({ children }) {
  const [flights, setFlights] = useState([])
  const [closures, setClosures] = useState([])
  const [config, setConfig] = useState(null)
  const [rehearsal, setRehearsal] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const flash = useCallback((msg) => {
    setError(String(msg))
    setTimeout(() => setError(''), 5000)
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [f, c, cfg, r] = await Promise.all([
        api.listFlights(),
        api.listClosures(),
        api.getConfig(),
        api.rehearse(),
      ])
      setFlights(f)
      setClosures(c)
      setConfig(cfg)
      setRehearsal(r)
    } catch (e) {
      flash(e.message)
    } finally {
      setLoading(false)
    }
  }, [flash])

  useEffect(() => {
    refresh()
  }, [refresh])

  const value = {
    flights,
    setFlights,
    closures,
    setClosures,
    config,
    setConfig,
    rehearsal,
    setRehearsal,
    loading,
    error,
    flash,
    refresh,
  }
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}

export function useStore() {
  return useContext(StoreContext)
}
