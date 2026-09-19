const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || JSON.stringify(body)
    } catch {
      /* keep status text */
    }
    throw new Error(`${res.status}: ${detail}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  health: () => request('/health'),
  getConfig: () => request('/config'),
  updateConfig: (data) =>
    request('/config', { method: 'PUT', body: JSON.stringify(data) }),

  listFlights: () => request('/flights'),
  createFlight: (data) =>
    request('/flights', { method: 'POST', body: JSON.stringify(data) }),
  updateFlight: (id, data) =>
    request(`/flights/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteFlight: (id) => request(`/flights/${id}`, { method: 'DELETE' }),

  listClosures: () => request('/closures'),
  createClosure: (data) =>
    request('/closures', { method: 'POST', body: JSON.stringify(data) }),
  deleteClosure: (id) => request(`/closures/${id}`, { method: 'DELETE' }),

  rehearse: () => request('/rehearse'),
  adjust: (data) =>
    request('/rehearse/adjust', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  autoResolve: () => request('/rehearse/auto-resolve', { method: 'POST' }),
  resetDemo: () => request('/rehearse/reset-demo', { method: 'POST' }),
}
