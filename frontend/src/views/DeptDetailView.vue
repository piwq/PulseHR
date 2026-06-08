<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PhCard from '../components/ui/PhCard.vue'
import PhButton from '../components/ui/PhButton.vue'
import PhIcon from '../components/ui/PhIcon.vue'
import PhSkeleton from '../components/ui/PhSkeleton.vue'
import PhEmptyState from '../components/ui/PhEmptyState.vue'
import PhModal from '../components/ui/PhModal.vue'
import PhSeverityBadge from '../components/ui/PhSeverityBadge.vue'
import { api } from '../lib/api'
import { sevLabel } from '../lib/severity'
import { useToasts } from '../stores/useToasts'

const route = useRoute()
const router = useRouter()
const toasts = useToasts()

const name = computed(() => decodeURIComponent(route.params.name))

const employees = ref([])
const analytics  = ref(null)
const loading   = ref(true)

async function loadAll() {
  loading.value = true
  try {
    ;[employees.value, analytics.value] = await Promise.all([
      api('/auth/employees'),
      api('/surveys/dashboard/'),
    ])
  } finally {
    loading.value = false
  }
}
onMounted(loadAll)

// Состав отдела
const roster = computed(() => employees.value.filter(e => (e.department || '') === name.value))

// Метрики отдела (из аналитики дашборда; может отсутствовать / быть скрытой при N<5)
const kpi = computed(() =>
  (analytics.value?.departments || []).find(d => d.department === name.value && !d.suppressed) || null,
)
const suppressed = computed(() =>
  (analytics.value?.departments || []).some(d => d.department === name.value && d.suppressed),
)

function fmt(v, dec = 1) { return v == null ? '—' : Number(v).toFixed(dec) }

// ── Управление составом ────────────────────────────────────────────
async function removeFromDept(emp) {
  try {
    const updated = await api(`/auth/employees/${emp.id}`, { method: 'PATCH', body: { department: '' } })
    const i = employees.value.findIndex(e => e.id === emp.id)
    if (i >= 0) employees.value[i] = updated
    toasts.push({ tone: 'low', badge: 'Готово', title: `${emp.name || emp.phone} убран(а) из отдела` })
  } catch {
    toasts.push({ tone: 'critical', badge: 'Ошибка', title: 'Не удалось обновить отдел' })
  }
}

// Модалка «Добавить сотрудника»
const addOpen = ref(false)
const addSearch = ref('')
const assignable = computed(() => {
  const q = addSearch.value.toLowerCase()
  return employees.value
    .filter(e => (e.department || '') !== name.value)
    .filter(e => !q || (`${e.name} ${e.phone} ${e.department}`).toLowerCase().includes(q))
})

async function assignToDept(emp) {
  try {
    const updated = await api(`/auth/employees/${emp.id}`, { method: 'PATCH', body: { department: name.value } })
    const i = employees.value.findIndex(e => e.id === emp.id)
    if (i >= 0) employees.value[i] = updated
    toasts.push({ tone: 'low', badge: 'Готово', title: `${emp.name || emp.phone} добавлен(а) в «${name.value}»` })
  } catch {
    toasts.push({ tone: 'critical', badge: 'Ошибка', title: 'Не удалось назначить отдел' })
  }
}
</script>

<template>
  <div v-if="loading" style="display:flex;flex-direction:column;gap:16px">
    <PhCard><PhSkeleton w="40%" :h="20" /><PhSkeleton w="100%" :h="60" :style="{ marginTop: '14px' }" /></PhCard>
    <PhCard><PhSkeleton w="100%" :h="20" v-for="i in 4" :key="i" :style="{ marginBottom: '10px' }" /></PhCard>
  </div>

  <div v-else class="route" style="display:flex;flex-direction:column;gap:16px">

    <!-- Назад -->
    <button class="back-link" @click="router.push('/depts')">
      <PhIcon name="arrow" :size="14" style="transform:rotate(180deg)" />Все отделы
    </button>

    <!-- Шапка отдела + метрики -->
    <PhCard>
      <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
        <div class="h2" style="font-size:20px">{{ name }}</div>
        <PhSeverityBadge v-if="kpi" :level="kpi.sev" pulse>{{ sevLabel(kpi.sev) }}</PhSeverityBadge>
        <span v-else class="badge badge--neutral"><span class="badge__dot" />нет данных</span>
      </div>

      <div class="dept-kpis">
        <div class="dept-kpi">
          <div class="dept-kpi__v">{{ fmt(kpi?.eng) }}<span class="dept-kpi__u">/5</span></div>
          <div class="dept-kpi__k">Вовлечённость</div>
        </div>
        <div class="dept-kpi">
          <div class="dept-kpi__v" :style="{ color: (kpi?.enps ?? 0) < 0 ? 'var(--sev-crit-text)' : 'var(--text)' }">
            {{ kpi?.enps == null ? '—' : (kpi.enps > 0 ? '+' : '') + kpi.enps }}
          </div>
          <div class="dept-kpi__k">eNPS</div>
        </div>
        <div class="dept-kpi">
          <div class="dept-kpi__v">{{ kpi?.part == null ? '—' : kpi.part + '%' }}</div>
          <div class="dept-kpi__k">Участие</div>
        </div>
        <div class="dept-kpi">
          <div class="dept-kpi__v">{{ roster.length }}</div>
          <div class="dept-kpi__k">Сотрудников</div>
        </div>
      </div>
      <p v-if="!kpi && suppressed" class="xs muted" style="margin-top:10px">
        Данных по отделу недостаточно для агрегата (защита анонимности, нужно ≥ 5 ответов).
      </p>
    </PhCard>

    <!-- Состав отдела -->
    <PhCard :pad="false">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 16px 10px">
        <div class="h3" style="font-size:15px">Сотрудники отдела</div>
        <PhButton variant="primary" icon="user" @click="addOpen = true; addSearch = ''">Добавить сотрудника</PhButton>
      </div>

      <div v-if="!roster.length" style="padding:8px 16px 24px">
        <PhEmptyState icon="user" title="В отделе пока никого нет"
          body="Назначьте сотрудников в этот отдел кнопкой «Добавить сотрудника»." />
      </div>

      <table v-else class="tbl">
        <thead>
          <tr><th>Имя / телефон</th><th>Роль</th><th style="text-align:right"></th></tr>
        </thead>
        <tbody>
          <tr v-for="e in roster" :key="e.id">
            <td>
              <div style="font-weight:600">{{ e.name || '—' }}</div>
              <div class="xs muted">{{ e.phone }}</div>
            </td>
            <td>
              <span class="badge" :class="e.role === 'hr' ? 'badge--low' : 'badge--neutral'">
                <span class="badge__dot" />{{ e.role === 'hr' ? 'HR' : 'Сотрудник' }}
              </span>
            </td>
            <td style="text-align:right">
              <PhButton variant="ghost" @click="removeFromDept(e)">Убрать из отдела</PhButton>
            </td>
          </tr>
        </tbody>
      </table>
    </PhCard>
  </div>

  <!-- Модалка добавления -->
  <PhModal :open="addOpen" :title="`Добавить в «${name}»`" @close="addOpen = false">
    <div style="display:flex;flex-direction:column;gap:10px">
      <input class="input" v-model="addSearch" placeholder="Поиск по имени, телефону, отделу…" style="font-size:14px" autofocus />
      <div class="assign-list">
        <div v-if="!assignable.length" class="sm muted" style="padding:16px;text-align:center">
          Нет сотрудников для добавления.
        </div>
        <div v-for="e in assignable" :key="e.id" class="assign-item" @click="assignToDept(e)">
          <div style="min-width:0;flex:1">
            <div class="sm" style="font-weight:600">{{ e.name || '—' }} <span class="xs muted">· {{ e.phone }}</span></div>
            <div class="xs muted">{{ e.department || 'без отдела' }}</div>
          </div>
          <PhIcon name="arrow" :size="14" style="color:var(--accent);flex:none" />
        </div>
      </div>
    </div>
    <template #footer>
      <div style="display:flex;justify-content:flex-end">
        <PhButton variant="ghost" @click="addOpen = false">Закрыть</PhButton>
      </div>
    </template>
  </PhModal>
</template>

<style scoped>
.back-link {
  display: inline-flex; align-items: center; gap: 6px; align-self: flex-start;
  background: none; border: none; cursor: pointer; font-family: inherit;
  font-size: 13px; color: var(--text-muted); padding: 2px 0; transition: color .12s;
}
.back-link:hover { color: var(--text); }

.dept-kpis {
  display: flex; gap: 28px; margin-top: 16px; flex-wrap: wrap;
}
.dept-kpi__v { font-size: 24px; font-weight: 800; letter-spacing: -0.02em; color: var(--text); font-variant-numeric: tabular-nums; }
.dept-kpi__u { font-size: 13px; font-weight: 500; color: var(--text-muted); margin-left: 2px; }
.dept-kpi__k { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

.assign-list { max-height: 320px; overflow-y: auto; border: 1px solid var(--line); border-radius: 10px; }
.assign-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; cursor: pointer; border-bottom: 1px solid var(--line); transition: background .1s;
}
.assign-item:last-child { border-bottom: none; }
.assign-item:hover { background: var(--bg-raised); }
</style>
