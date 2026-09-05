import type { Instrument } from './types'

const isViteDev = window.location.port === '5173'
export const API_BASE = import.meta.env.VITE_API_BASE ?? (isViteDev ? 'http://127.0.0.1:8000' : window.location.origin)
export const WS_URL = import.meta.env.VITE_WS_URL ?? (isViteDev ? 'ws://127.0.0.1:8000/ws/market' : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/market`)

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers ?? {}) },
    ...options,
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const payload = await response.json()
      detail = payload.detail ?? detail
    } catch {
      // keep status text
    }
    throw new Error(detail)
  }
  return response.json()
}

export function searchInstruments(query: string) {
  return request<{ instruments: Instrument[] }>('/live/search', {
    method: 'POST',
    body: JSON.stringify({ query }),
  })
}

export function startLive(instrument: Instrument, interval: string) {
  return request('/live/start', {
    method: 'POST',
    body: JSON.stringify({ instrument, interval }),
  })
}

export function stopLive() {
  return request('/live/stop', { method: 'POST' })
}

export function setIntervalRemote(interval: string) {
  return request('/live/interval', {
    method: 'POST',
    body: JSON.stringify({ interval }),
  })
}
