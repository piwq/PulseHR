<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PhLogo from '../components/ui/PhLogo.vue'
import PhIcon from '../components/ui/PhIcon.vue'
import PhButton from '../components/ui/PhButton.vue'
import PhSeverityBadge from '../components/ui/PhSeverityBadge.vue'
import PhToastHost from '../components/ui/PhToastHost.vue'
import { api } from '../lib/api'
import { useToasts } from '../stores/useToasts'
import { useAuth } from '../stores/useAuth'
import { useAppAction } from '../stores/useAppAction'
import { sevLabel } from '../lib/severity'

const route = useRoute()
const router = useRouter()
const toasts = useToasts()
const auth = useAuth()

const NAV = [
  { group: 'Обзор' },
  { id: 'dashboard', label: 'Дашборд', icon: 'grid', path: '/' },
  { id: 'depts', label: 'Отделы', icon: 'trend', path: '/depts' },
  { id: 'surveys', label: 'Опросы', icon: 'survey', path: '/surveys' },
  { id: 'comparison', label: 'Сравнение волн', icon: 'clock', path: '/comparison' },
  { id: 'ai-report', label: 'ИИ-отчёт', icon: 'spark', path: '/ai-report' },
  { group: 'Команда' },
  { id: 'employees', label: 'Сотрудники', icon: 'user', path: '/employees' },
  { group: 'Сигналы' },
  { id: 'alerts', label: 'Алерты', icon: 'alert', path: '/alerts' },
  { id: 'channels', label: 'Каналы', icon: 'bell', path: '/channels' },
  { id: 'history', label: 'История', icon: 'clock', path: '/history' },
]

const title = computed(() => route.meta.title || 'PulseHR')
const sub = computed(() => route.meta.sub || '')

const notifOpen = ref(false)
const notifItems = ref([])
async function toggleNotif() {
  notifOpen.value = !notifOpen.value
  if (notifOpen.value) {
    toasts.markAllRead()
    try { notifItems.value = await api('/insights/recent/') } catch { /* ignore */ }
  }
}

function sevFromScore(s) { return s >= 3 ? 'critical' : 'medium' }
function logout() { auth.logout(); router.push('/login') }

const appAction = useAppAction()
const currentAction = computed(() => route.meta.action || null)
function handleAction() {
  if (!currentAction.value) return
  if (currentAction.value.path) router.push(currentAction.value.path)
  else appAction.fire()
}

// живой поток инсайтов → designed toast
const SEEN_KEY = 'ph_last_insight_id'
let es = null
onMounted(() => {
  try {
    const since = localStorage.getItem(SEEN_KEY) || '0'
    es = new EventSource(`/api/insights/alerts/stream/?since=${since}`)
    es.onmessage = (e) => {
      let data
      try { data = JSON.parse(e.data) } catch { return }
      localStorage.setItem(SEEN_KEY, String(data.id))
      toasts.push({
        tone: data.severity >= 3 ? 'critical' : 'medium',
        badge: sevLabel(sevFromScore(data.severity)),
        title: `${data.department || 'Отдел'}: ${data.severity >= 3 ? 'критично' : 'внимание'}`,
        body: data.summary,
        actions: [{ id: 'open-dept', label: 'Открыть отдел', variant: 'primary' }],
      })
    }
    // Тихая ошибка — EventSource переподключится автоматически
    es.onerror = () => {}
  } catch { /* SSE not supported */ }
})
onBeforeUnmount(() => es && es.close())
</script>

<template>
  <div class="shell" @mousedown="notifOpen && (notifOpen = false)">
    <aside class="sidebar">
      <div class="sidebar__brand"><PhLogo :mark-size="28" :mark-radius="8" :wordmark-size="16" /></div>
      <nav style="display:flex;flex-direction:column;gap:2px">
        <template v-for="(n, i) in NAV" :key="i">
          <div v-if="n.group" class="sidebar__group">{{ n.group }}</div>
          <RouterLink v-else :to="n.path" custom v-slot="{ navigate, isExactActive, isActive }">
            <button class="navitem" :class="{ active: n.path === '/' ? isExactActive : isActive }" @click="navigate">
              <PhIcon :name="n.icon" :size="16" class="ico" />{{ n.label }}
            </button>
          </RouterLink>
        </template>
      </nav>
      <div class="sidebar__foot">
        <div class="avatar" style="cursor:pointer" title="Мой профиль" @click="router.push('/profile')">{{ auth.initials }}</div>
        <div style="min-width:0;flex:1;cursor:pointer" title="Мой профиль" @click="router.push('/profile')">
          <div class="sm" style="font-weight:600;white-space:nowrap">{{ auth.employee?.name || auth.employee?.phone }}</div>
          <div class="xs muted">HR-руководитель</div>
        </div>
        <button class="iconbtn" style="width:30px;height:30px;border:0;background:none" @click="logout" title="Выйти">
          <PhIcon name="logout" :size="15" />
        </button>
      </div>
    </aside>

    <div class="main">
      <PhToastHost />
      <header class="topbar">
        <div>
          <div class="topbar__title">{{ title }}</div>
          <div class="topbar__sub">{{ sub }}</div>
        </div>
        <div class="topbar__actions">
          <div style="position:relative" @mousedown.stop>
            <button class="iconbtn" @click="toggleNotif" title="Уведомления">
              <PhIcon name="bell" :size="17" />
              <span v-if="toasts.unread > 0" class="bell-badge pulse">{{ toasts.unread }}</span>
            </button>
            <div v-if="notifOpen" class="dropdown" @mousedown.stop>
              <div class="dropdown__head">
                <div class="sm" style="font-weight:700">Уведомления</div>
                <a class="xs" style="color:var(--accent-text);font-weight:600;cursor:pointer" @click="notifOpen = false">Закрыть</a>
              </div>
              <div v-if="notifItems.length === 0" style="padding:18px" class="sm muted">Сигналов пока нет.</div>
              <div v-for="it in notifItems" :key="it.id" class="dropdown__item">
                <div style="margin-top:2px">
                  <PhSeverityBadge :level="sevFromScore(it.severity)" :pulse="it.severity >= 3">{{ sevLabel(sevFromScore(it.severity)) }}</PhSeverityBadge>
                </div>
                <div style="min-width:0">
                  <div class="sm" style="font-weight:600">{{ it.department || 'Отдел' }}</div>
                  <div class="xs muted" style="margin-top:2px">{{ it.summary }}</div>
                </div>
              </div>
            </div>
          </div>
          <PhButton v-if="currentAction" variant="primary" :icon="currentAction.icon" @click="handleAction">
            {{ currentAction.label }}
          </PhButton>
        </div>
      </header>

      <div class="content"><div class="content__inner"><RouterView /></div></div>
    </div>
  </div>
</template>
