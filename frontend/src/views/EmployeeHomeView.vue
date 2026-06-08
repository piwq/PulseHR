<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PhLogo from '../components/ui/PhLogo.vue'
import PhIcon from '../components/ui/PhIcon.vue'
import PhButton from '../components/ui/PhButton.vue'
import PhCard from '../components/ui/PhCard.vue'
import PhEmptyState from '../components/ui/PhEmptyState.vue'
import { api } from '../lib/api'
import { useAuth } from '../stores/useAuth'
import { enablePush, pushSupported } from '../lib/push'

const router = useRouter()
const auth = useAuth()

const surveys = ref([])
const completed = ref([])
const loading = ref(true)
const pushDone = ref(localStorage.getItem('push_optin_done') === '1')
const pushMsg = ref('')
const notifOpen = ref(false)

// Профиль
const profileName = ref(auth.employee?.name || '')
const profileDept = ref(auth.employee?.department || '')
const profileDepts = ref([])
const profileSaving = ref(false)
const profileOpen = ref(!auth.employee?.department)

onMounted(async () => {
  load()
  try { profileDepts.value = await api('/auth/departments') } catch { /* ignore */ }
})

async function load() {
  loading.value = true
  try {
    [surveys.value, completed.value] = await Promise.all([
      api('/me/surveys/'),
      api('/me/surveys/completed/').catch(() => []),
    ])
  } finally { loading.value = false }
}

async function saveProfile() {
  profileSaving.value = true
  try {
    const updated = await api('/auth/me', {
      method: 'PATCH',
      body: { name: profileName.value.trim(), department: profileDept.value.trim() },
    })
    auth.employee = updated
    profileOpen.value = false
  } finally {
    profileSaving.value = false
  }
}

async function turnOnPush() {
  pushMsg.value = ''
  try {
    if (!auth.employee.consent_active) await auth.giveConsent()
    await enablePush()
    localStorage.setItem('push_optin_done', '1')
    pushDone.value = true
    pushMsg.value = 'Push-уведомления включены'
  } catch (e) {
    pushMsg.value = 'Не удалось включить: ' + e.message
  }
}
function dismissPush() { localStorage.setItem('push_optin_done', '1'); pushDone.value = true }
function logout() { auth.logout(); router.push('/login') }
</script>

<template>
  <div style="min-height:100vh;max-width:640px;margin:0 auto;padding:20px 18px" @mousedown="notifOpen = false">
    <header style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px">
      <PhLogo :mark-size="26" :mark-radius="7" :wordmark-size="16" :gap="9" />
      <div style="display:flex;align-items:center;gap:8px">
        <div style="position:relative" @mousedown.stop>
          <button class="iconbtn" title="Уведомления" @click="notifOpen = !notifOpen">
            <PhIcon name="bell" :size="17" />
            <span v-if="surveys.length > 0" class="bell-badge pulse">{{ surveys.length }}</span>
          </button>
          <div v-if="notifOpen" class="dropdown" @mousedown.stop style="right:0;left:auto;min-width:280px">
            <div class="dropdown__head">
              <div class="sm" style="font-weight:700">Уведомления</div>
              <a class="xs" style="color:var(--accent-text);font-weight:600;cursor:pointer" @click="router.push('/me/notifications')">Настройки</a>
            </div>
            <div v-if="surveys.length === 0" style="padding:18px" class="sm muted">Новых опросов нет.</div>
            <div v-for="s in surveys" :key="s.id" class="dropdown__item" style="cursor:pointer" @click="router.push(`/s/${s.id}`); notifOpen = false">
              <div style="margin-top:2px;color:var(--accent-text)"><PhIcon name="survey" :size="15" /></div>
              <div style="min-width:0">
                <div class="sm" style="font-weight:600">{{ s.title }}</div>
                <div class="xs muted" style="margin-top:2px">{{ s.question_count }} вопросов · нажмите, чтобы пройти</div>
              </div>
            </div>
          </div>
        </div>
        <button class="iconbtn" title="Выйти" @click="logout"><PhIcon name="logout" :size="16" /></button>
      </div>
    </header>

    <!-- Профиль (всегда виден; при первом входе — развёрнут) -->
    <PhCard style="margin-bottom:16px" :style="!auth.employee?.department ? 'border:1px solid var(--accent-soft)' : ''">
      <div style="display:flex;align-items:center;gap:12px;cursor:pointer" @click="profileOpen = !profileOpen">
        <div style="color:var(--accent-text)"><PhIcon name="user" :size="18" /></div>
        <div style="flex:1;min-width:0">
          <div class="sm" style="font-weight:600">{{ auth.employee?.name || auth.employee?.phone }}</div>
          <div class="xs muted">{{ auth.employee?.department || 'без отдела' }}</div>
        </div>
        <PhIcon name="arrow" :size="13" :style="{ transform: profileOpen ? 'rotate(-90deg)' : 'rotate(90deg)', transition: 'transform .18s', color: 'var(--text-muted)' }" />
      </div>
      <div v-if="profileOpen" style="margin-top:14px;padding-top:14px;border-top:1px solid var(--line);display:flex;flex-direction:column;gap:8px">
        <input class="input" v-model="profileName" placeholder="Ваше имя" style="font-size:14px" />
        <select v-if="profileDepts.length" class="select" v-model="profileDept" style="font-size:14px">
          <option value="">— без отдела —</option>
          <option v-for="d in profileDepts" :key="d" :value="d">{{ d }}</option>
        </select>
        <input v-else class="input" v-model="profileDept" placeholder="Отдел" style="font-size:14px" />
        <PhButton variant="primary" :disabled="profileSaving" @click.stop="saveProfile">
          {{ profileSaving ? 'Сохранение…' : 'Сохранить' }}
        </PhButton>
      </div>
    </PhCard>

    <!-- Мягкий промпт Web Push -->
    <PhCard v-if="!pushDone && pushSupported()" style="margin-bottom:16px">
      <div style="display:flex;gap:14px;align-items:flex-start">
        <div style="margin-top:2px;color:var(--accent-text)"><PhIcon name="bell" :size="20" /></div>
        <div style="flex:1">
          <div class="h3" style="font-size:15px;margin-bottom:4px">Не пропустите ни один опрос</div>
          <p class="sm muted">Получайте уведомления о новых опросах прямо в браузере.</p>
          <p v-if="pushMsg" class="xs" style="margin-top:8px;color:var(--accent-text)">{{ pushMsg }}</p>
          <div style="display:flex;gap:8px;margin-top:12px">
            <PhButton variant="primary" @click="turnOnPush">Включить</PhButton>
            <PhButton variant="ghost" @click="dismissPush">Не сейчас</PhButton>
          </div>
        </div>
      </div>
    </PhCard>

    <h1 class="h2" style="margin-bottom:14px">Доступные опросы</h1>

    <div v-if="loading" class="muted sm">Загрузка…</div>
    <PhCard v-else-if="surveys.length === 0">
      <PhEmptyState icon="check" title="Всё пройдено" body="Новых опросов для вас сейчас нет." />
    </PhCard>

    <div v-else style="display:flex;flex-direction:column;gap:12px">
      <PhCard v-for="s in surveys" :key="s.id" hover>
        <div style="display:flex;align-items:center;gap:14px">
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:10px">
              <div class="h3" style="font-size:15px">{{ s.title }}</div>
              <span class="badge" :class="s.mode === 'anonymous' ? 'badge--low' : 'badge--neutral'">
                <span class="badge__dot" />{{ s.mode === 'anonymous' ? 'анонимный' : 'идентифицированный' }}
              </span>
            </div>
            <p class="sm muted" style="margin-top:4px">{{ s.question_count }} вопросов · ~{{ s.question_count }} мин</p>
          </div>
          <PhButton variant="primary" icon-right="arrow" @click="router.push(`/s/${s.id}`)">Пройти</PhButton>
        </div>
      </PhCard>
    </div>

    <!-- Пройденные опросы -->
    <template v-if="!loading && completed.length > 0">
      <h2 class="h2" style="margin-top:32px;margin-bottom:14px;font-size:15px;color:var(--text-secondary)">Пройденные</h2>
      <div style="display:flex;flex-direction:column;gap:8px">
        <PhCard v-for="s in completed" :key="s.id">
          <div style="display:flex;align-items:center;gap:14px">
            <div style="color:var(--sev-low-text);flex-shrink:0"><PhIcon name="check" :size="16" /></div>
            <div style="flex:1;min-width:0">
              <div style="display:flex;align-items:center;gap:10px">
                <div class="sm" style="font-weight:600;color:var(--text-secondary)">{{ s.title }}</div>
                <span class="badge badge--low"><span class="badge__dot" />пройден</span>
              </div>
              <p class="xs muted" style="margin-top:2px">
                {{ s.question_count }} вопросов
                <template v-if="s.completed_at"> · {{ new Date(s.completed_at).toLocaleDateString('ru', { day: 'numeric', month: 'long' }) }}</template>
              </p>
            </div>
          </div>
        </PhCard>
      </div>
    </template>
  </div>
</template>
