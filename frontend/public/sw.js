// PulseHR Service Worker — обработка Web Push и клика по уведомлению.
self.addEventListener('push', (event) => {
  let data = {}
  try { data = event.data.json() } catch (e) { /* not json */ }
  const title = data.title || 'PulseHR'
  event.waitUntil(self.registration.showNotification(title, {
    body: data.body || '',
    data: { url: data.url || '/', survey_id: data.survey_id },
    tag: data.survey_id ? 'survey-' + data.survey_id : undefined, // дедупликация
  }))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = (event.notification.data && event.notification.data.url) || '/'
  event.waitUntil(clients.openWindow(url))
})
