<script setup>
import { ref, computed, onMounted } from 'vue'
import PhCard from '../components/ui/PhCard.vue'
import PhButton from '../components/ui/PhButton.vue'
import PhIcon from '../components/ui/PhIcon.vue'
import { api } from '../lib/api'
import { useAuth } from '../stores/useAuth'
import { useToasts } from '../stores/useToasts'

const auth = useAuth()
const toasts = useToasts()

const name = ref(auth.employee?.name || '')
const department = ref(auth.employee?.department || '')
const city = ref(auth.employee?.city || '')
const depts = ref([])
const saving = ref(false)

onMounted(async () => {
  try { depts.value = await api('/auth/departments') } catch {}
})

const consentActive = computed(() => !!auth.employee?.consent_active)

const dirty = computed(() =>
  name.value.trim() !== (auth.employee?.name || '') ||
  department.value.trim() !== (auth.employee?.department || '') ||
  city.value.trim() !== (auth.employee?.city || ''),
)

async function save() {
  saving.value = true
  try {
    const updated = await api('/auth/me', {
      method: 'PATCH',
      body: { name: name.value.trim(), department: department.value.trim(), city: city.value.trim() },
    })
    auth.employee = updated
    toasts.push({ tone: 'low', badge: 'Готово', title: 'Профиль обновлён' })
  } catch {
    toasts.push({ tone: 'critical', badge: 'Ошибка', title: 'Не удалось сохранить' })
  } finally {
    saving.value = false
  }
}

async function toggleConsent() {
  try {
    const action = consentActive.value ? 'revoke' : 'give'
    const updated = await api('/auth/consent', { method: 'POST', body: { action } })
    auth.employee = updated
  } catch {
    toasts.push({ tone: 'critical', badge: 'Ошибка', title: 'Не удалось изменить статус согласия' })
  }
}
</script>

<template>
  <div class="route" style="display:flex;flex-direction:column;gap:16px;max-width:560px">

    <!-- Аватар + телефон + роль -->
    <PhCard>
      <div style="display:flex;align-items:center;gap:16px">
        <div class="av-big">{{ auth.initials }}</div>
        <div>
          <div class="h2" style="font-size:18px">{{ auth.employee?.name || 'Без имени' }}</div>
          <div class="sm muted" style="margin-top:3px">{{ auth.employee?.phone }}</div>
          <span class="badge badge--low" style="margin-top:8px;display:inline-flex">
            <span class="badge__dot" />HR-руководитель
          </span>
        </div>
      </div>
    </PhCard>

    <!-- Редактирование данных -->
    <PhCard>
      <div class="h3" style="font-size:15px;margin-bottom:16px">Личные данные</div>
      <div style="display:flex;flex-direction:column;gap:12px">

        <div>
          <label class="xs muted" style="display:block;margin-bottom:4px">Имя</label>
          <input class="input" v-model="name" placeholder="Ваше имя" style="font-size:14px" />
        </div>

        <div>
          <label class="xs muted" style="display:block;margin-bottom:4px">Отдел</label>
          <select v-if="depts.length" class="select" v-model="department" style="font-size:14px">
            <option value="">— без отдела —</option>
            <option v-for="d in depts" :key="d" :value="d">{{ d }}</option>
          </select>
          <input v-else class="input" v-model="department" placeholder="Отдел" style="font-size:14px" />
        </div>

        <div>
          <label class="xs muted" style="display:block;margin-bottom:4px">Город</label>
          <input class="input" v-model="city" placeholder="Город" style="font-size:14px" />
        </div>

        <div>
          <label class="xs muted" style="display:block;margin-bottom:4px">Телефон</label>
          <div class="input" style="font-size:14px;display:flex;align-items:center;gap:8px;background:var(--bg-raised);cursor:default">
            <PhIcon name="lock" :size="13" style="color:var(--text-muted);flex-shrink:0" />
            <span style="color:var(--text-muted)">{{ auth.employee?.phone }}</span>
            <span class="xs muted" style="margin-left:auto">нельзя изменить</span>
          </div>
        </div>

      </div>
      <PhButton variant="primary" style="margin-top:18px" :disabled="!dirty || saving" @click="save">
        {{ saving ? 'Сохранение…' : 'Сохранить изменения' }}
      </PhButton>
    </PhCard>

    <!-- 152-ФЗ согласие -->
    <PhCard>
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap">
        <div style="flex:1;min-width:0">
          <div class="h3" style="font-size:15px">Согласие на коммуникации</div>
          <p class="xs muted" style="margin-top:4px">
            152-ФЗ: {{ consentActive
              ? 'Согласие дано — уведомления включены.'
              : 'Согласие отозвано — рассылки остановлены.' }}
          </p>
        </div>
        <div style="display:flex;align-items:center;gap:10px;flex-shrink:0">
          <span class="badge" :class="consentActive ? 'badge--low' : 'badge--neutral'">
            <span class="badge__dot" />{{ consentActive ? 'активно' : 'отозвано' }}
          </span>
          <PhButton :variant="consentActive ? 'ghost' : 'primary'" @click="toggleConsent">
            {{ consentActive ? 'Отозвать' : 'Дать согласие' }}
          </PhButton>
        </div>
      </div>
    </PhCard>

  </div>
</template>

<style scoped>
.av-big {
  width: 52px; height: 52px; border-radius: 50%;
  background: var(--accent-soft, rgba(99,102,241,.15));
  color: var(--accent-text); font-weight: 800; font-size: 18px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; letter-spacing: -0.02em;
}
</style>
