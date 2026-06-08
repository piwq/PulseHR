// Тонкий fetch-клиент: базовый префикс + токен в заголовке Authorization.
const BASE = '/api'
const TOKEN_KEY = 'pulse_token'

export function getToken() { return localStorage.getItem(TOKEN_KEY) || '' }
export function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t)
  else localStorage.removeItem(TOKEN_KEY)
}

export async function api(path, { method = 'GET', body, auth = true } = {}) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth && getToken()) headers['Authorization'] = 'Token ' + getToken()
  const res = await fetch(BASE + path, {
    method, headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = new Error('HTTP ' + res.status)
    err.status = res.status
    try { err.data = await res.json() } catch { /* ignore */ }
    throw err
  }
  if (res.status === 204) return null
  const ct = res.headers.get('content-type') || ''
  return ct.includes('application/json') ? res.json() : res
}
