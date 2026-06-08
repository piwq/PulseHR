<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PhLogo from '../components/ui/PhLogo.vue'
import PhIcon from '../components/ui/PhIcon.vue'
import PhButton from '../components/ui/PhButton.vue'
import PhCard from '../components/ui/PhCard.vue'
import { api } from '../lib/api'
import { useAuth } from '../stores/useAuth'

const router = useRouter()
const auth = useAuth()
const prefs = ref(null)
const devices = ref([])
const tgCode = ref('')
const copied = ref(false)

const CHANNELS = [
  { key: 'web_push', label: 'Web Push', hint: 'Браузерные уведомления (основной канал)' },
  { key: 'telegram', label: 'Telegram', hint: 'Сообщения от бота' },
  { key: 'sms', label: 'SMS', hint: 'Резервный канал' },
  { key: 'email', label: 'E-mail', hint: 'Напоминания на почту' },
]
const TIMES = [['any', 'Любое'], ['morning', 'Утром'], ['day', 'Днём'], ['evening', 'Вечером']]

onMounted(async () => {
  ;[prefs.value, devices.value] = await Promise.all([
    api('/notifications/prefs'),
    api('/notifications/devices'),
  ])
  // Обновим данные сотрудника чтобы получить актуальный telegram_linked
  await auth.refresh()
})

async function save() {
  prefs.value = await api('/notifications/prefs', { method: 'PUT', body: prefs.value })
}
async function removeDevice(id) {
  await api(`/notifications/devices/${id}`, { method: 'DELETE' })
  devices.value = devices.value.filter((d) => d.id !== id)
}
async function linkTelegram() {
  const res = await api('/notifications/telegram/qr')
  tgCode.value = res.code
  window.open(res.deep_link, '_blank')
}

async function copyCode() {
  await navigator.clipboard.writeText(`/start ${tgCode.value}`)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

async function unlinkTelegram() {
  await api('/notifications/telegram/unlink', { method: 'DELETE' })
  tgCode.value = ''
  await auth.refresh()
}

const tgLinked = () => auth.employee?.telegram_linked
</script>

<template>
  <div style="height:100vh;overflow-y:auto">
    <div style="max-width:600px;margin:0 auto;padding:20px 18px 40px">
      <header style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px">
        <PhLogo :mark-size="26" :mark-radius="7" :wordmark-size="16" :gap="9" />
        <button class="iconbtn" title="Назад" @click="router.push('/me')"><PhIcon name="arrow" :size="16" /></button>
      </header>

      <h1 class="h2" style="margin-bottom:14px">Уведомления</h1>

      <PhCard v-if="prefs" style="margin-bottom:16px">
        <div class="h3" style="font-size:15px;margin-bottom:14px">Каналы</div>
        <label v-for="c in CHANNELS" :key="c.key"
          style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--line);cursor:pointer">
          <input type="checkbox" v-model="prefs[c.key]" @change="save"
            style="accent-color:var(--accent);width:17px;height:17px" />
          <div style="flex:1">
            <div class="sm" style="font-weight:600">{{ c.label }}</div>
            <div class="xs muted">{{ c.hint }}</div>
          </div>
        </label>
        <p class="xs muted" style="margin-top:12px">
          Критичные опросы (обязательные, по 152-ФЗ) доставляются по каскаду независимо от настроек.
        </p>
      </PhCard>

      <PhCard v-if="prefs" style="margin-bottom:16px">
        <div class="h3" style="font-size:15px;margin-bottom:12px">Предпочтительное время</div>
        <select class="select" v-model="prefs.preferred_time" @change="save">
          <option v-for="[v, l] in TIMES" :key="v" :value="v">{{ l }}</option>
        </select>
        <label style="display:flex;align-items:center;gap:10px;margin-top:14px">
          <span class="sm muted">Не беспокоить до:</span>
          <input type="date" class="input" style="width:auto"
            :value="prefs.dnd_until ? prefs.dnd_until.slice(0,10) : ''"
            @change="prefs.dnd_until = $event.target.value ? $event.target.value + 'T00:00:00Z' : null; save()" />
        </label>
      </PhCard>

      <PhCard style="margin-bottom:16px">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px">
          <div style="min-width:0">
            <div style="display:flex;align-items:center;gap:8px">
              <div class="h3" style="font-size:15px">Telegram</div>
              <span v-if="tgLinked()" class="badge badge--low" style="font-size:11px">
                <span class="badge__dot" />привязан
              </span>
            </div>
            <p class="xs muted" style="margin-top:2px">
              {{ tgLinked() ? 'Бот привязан — опросы приходят в чат.' : 'Привяжите бот, чтобы получать опросы в чат.' }}
            </p>
          </div>
          <PhButton v-if="tgLinked()" variant="ghost" @click="unlinkTelegram">Отвязать</PhButton>
          <PhButton v-else variant="secondary" @click="linkTelegram">Привязать</PhButton>
        </div>
        <div v-if="tgCode" style="margin-top:14px;padding-top:14px;border-top:1px solid var(--line)">
          <p class="xs muted" style="margin-bottom:8px">Или введите этот код вручную в боте <b>@HireFlowwBot</b>:</p>
          <div style="display:flex;align-items:center;gap:8px">
            <code style="flex:1;background:var(--surface-raised,#1e1e2e);border:1px solid var(--line);border-radius:6px;padding:7px 10px;font-size:13px;font-family:monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">/start {{ tgCode }}</code>
            <button class="iconbtn" style="flex-shrink:0;width:34px;height:34px;border:1px solid var(--line);border-radius:6px" @click="copyCode" :title="copied ? 'Скопировано!' : 'Копировать'">
              <PhIcon :name="copied ? 'check' : 'copy'" :size="14" />
            </button>
          </div>
          <p class="xs muted" style="margin-top:6px">Отправьте боту — он подтвердит привязку, обновите страницу.</p>
        </div>
      </PhCard>

      <PhCard>
        <div class="h3" style="font-size:15px;margin-bottom:10px">Устройства с push</div>
        <p v-if="devices.length === 0" class="sm muted">Нет активных подписок.</p>
        <div v-for="d in devices" :key="d.id"
          style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--line)">
          <PhIcon name="grid" :size="16" style="color:var(--text-muted)" />
          <div style="flex:1;min-width:0" class="sm">{{ d.user_agent || 'Устройство' }}</div>
          <button class="iconbtn" style="width:30px;height:30px" @click="removeDevice(d.id)">
            <PhIcon name="x" :size="14" />
          </button>
        </div>
      </PhCard>
    </div>
  </div>
</template>
