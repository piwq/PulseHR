import { defineStore } from 'pinia'
import { api, getToken, setToken } from '../lib/api'

// Реальная OTP-авторизация по телефону. Токен в localStorage, профиль с ролью — с бэкенда.
export const useAuth = defineStore('auth', {
  state: () => ({
    token: getToken(),
    employee: null,
    ready: false,
  }),
  getters: {
    authenticated: (s) => !!s.employee,
    isHr: (s) => s.employee?.role === 'hr',
    initials: (s) => (s.employee?.name || s.employee?.phone || '??')
      .split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase(),
  },
  actions: {
    async requestCode(phone) {
      return api('/auth/request-code', { method: 'POST', body: { phone }, auth: false })
    },
    async verify(phone, code) {
      const data = await api('/auth/verify', { method: 'POST', body: { phone, code }, auth: false })
      setToken(data.token)
      this.token = data.token
      this.employee = data.employee
      return data
    },
    async restore() {
      // Восстановление сессии при загрузке приложения.
      if (this.token) {
        try { this.employee = await api('/auth/me') } catch { this.logout() }
      }
      this.ready = true
    },
    async giveConsent() {
      this.employee = await api('/auth/consent', { method: 'POST', body: { action: 'give' } })
    },
    async refresh() {
      if (this.token) {
        try { this.employee = await api('/auth/me') } catch { /* ignore */ }
      }
    },
    logout() {
      setToken('')
      this.token = ''
      this.employee = null
    },
  },
})
