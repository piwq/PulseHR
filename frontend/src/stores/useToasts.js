import { defineStore } from 'pinia'

// Toast viewport state + unread bell counter. The critical "wow" toast is the
// demo centrepiece; it can be pushed manually (demo button) or by the live SSE
// alert stream wired in AppLayout.

let seq = 1

export const useToasts = defineStore('toasts', {
  state: () => ({
    items: [],
    unread: 0,
  }),
  actions: {
    push(toast) {
      const id = ++seq
      this.items.push({ id, time: 'только что', ...toast })
      this.unread += 1
      setTimeout(() => this.remove(id), 8000) // auto-dismiss
      return id
    },
    remove(id) {
      this.items = this.items.filter((t) => t.id !== id)
    },
    markAllRead() {
      this.unread = 0
    },
  },
})
