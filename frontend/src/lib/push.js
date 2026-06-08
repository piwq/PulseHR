import { api } from './api'

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)))
}

export function pushSupported() {
  return 'serviceWorker' in navigator && 'PushManager' in window
}

// Регистрирует SW, спрашивает разрешение и сохраняет подписку на сервере (связь с user_id).
export async function enablePush() {
  if (!pushSupported()) throw new Error('Браузер не поддерживает Web Push')
  const reg = await navigator.serviceWorker.register('/sw.js')
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') throw new Error('Разрешение не выдано')
  const { public_key } = await api('/notifications/vapid-public-key', { auth: false })
  if (!public_key) throw new Error('VAPID не настроен на сервере')
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(public_key),
  })
  await api('/notifications/push/subscribe', {
    method: 'POST',
    body: { subscription: sub.toJSON(), user_agent: navigator.userAgent },
  })
  return true
}
