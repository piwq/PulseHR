<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import PhCard from '../components/ui/PhCard.vue'
import PhSeverityBadge from '../components/ui/PhSeverityBadge.vue'
import PhEmptyState from '../components/ui/PhEmptyState.vue'
import PhSparkline from '../components/charts/PhSparkline.vue'
import PhModal from '../components/ui/PhModal.vue'
import PhButton from '../components/ui/PhButton.vue'
import { api } from '../lib/api'
import { sevLabel, sevColor } from '../lib/severity'
import { useAppAction } from '../stores/useAppAction'

const analytics = ref(null)   // /surveys/dashboard/ — отделы с реальными данными
const allDepts = ref([])      // /auth/departments — полный список отделов

async function loadAll() {
  ;[analytics.value, allDepts.value] = await Promise.all([
    api('/surveys/dashboard/'),
    api('/auth/departments'),
  ])
}
onMounted(loadAll)

// Объединяем: все отделы + аналитика там где есть
const rows = computed(() => {
  const analyticsMap = {}
  for (const d of (analytics.value?.departments || [])) {
    if (!d.suppressed) analyticsMap[d.department] = d
  }
  const trend = analytics.value?.trend

  return allDepts.value.map((name) => {
    const d = analyticsMap[name]
    const trendSeries = trend?.departments?.find((s) => s.department === name)
    const trendVals = (trendSeries?.values || []).filter((v) => v != null)
    return {
      department: name,
      eng: d?.eng ?? null,
      enps: d?.enps ?? null,
      part: d?.part ?? null,
      sev: d?.sev ?? 'low',
      note: d?.note ?? '—',
      trendVals,
      hasData: !!d,
    }
  })
})

// Модалка «Новый отдел»
const modalOpen = ref(false)
const newDeptName = ref('')
const deptError = ref('')
const saving = ref(false)

const appAction = useAppAction()
watch(() => appAction.trigger, () => { modalOpen.value = true; newDeptName.value = ''; deptError.value = '' })

// Сброс ошибки при изменении поля
watch(newDeptName, () => { deptError.value = '' })

const deptExists = computed(() =>
  allDepts.value.some((d) => d.toLowerCase() === newDeptName.value.trim().toLowerCase()),
)

async function createDept() {
  const name = newDeptName.value.trim()
  if (!name) return
  if (deptExists.value) { deptError.value = `Отдел «${name}» уже существует`; return }
  saving.value = true
  deptError.value = ''
  try {
    await api('/auth/departments', { method: 'POST', body: { name } })
    modalOpen.value = false
    await loadAll()
  } catch (e) {
    deptError.value = e.data?.detail || 'Ошибка при создании'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <PhCard v-if="rows.length === 0">
    <PhEmptyState icon="trend" title="Нет отделов" body="Создайте первый отдел или добавьте сотрудников." />
  </PhCard>

  <PhCard v-else :pad="false" class="route">
    <table class="tbl">
      <thead>
        <tr>
          <th>Отдел</th><th>Тренд</th><th>Вовлечённость</th><th>eNPS</th><th>Участие</th><th style="text-align:right">Статус</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in rows" :key="d.department">
          <td style="font-weight:600">{{ d.department }}</td>
          <td>
            <PhSparkline v-if="d.trendVals.length > 1" :values="d.trendVals" :color="sevColor(d.sev)" />
            <span v-else class="xs muted">—</span>
          </td>
          <td class="num tnum" style="font-weight:600">
            {{ d.eng == null ? '—' : d.eng.toFixed(1) }}
          </td>
          <td class="num tnum" :style="{ color: d.enps != null && d.enps < 0 ? 'var(--sev-crit-text)' : 'var(--text-secondary)' }">
            {{ d.enps == null ? '—' : (d.enps > 0 ? '+' : '') + d.enps }}
          </td>
          <td class="num tnum">{{ d.part == null ? '—' : d.part + '%' }}</td>
          <td style="text-align:right">
            <span v-if="d.hasData">
              <PhSeverityBadge :level="d.sev" pulse>{{ sevLabel(d.sev) }}</PhSeverityBadge>
            </span>
            <span v-else class="badge badge--neutral"><span class="badge__dot" />нет данных</span>
          </td>
        </tr>
      </tbody>
    </table>
  </PhCard>

  <PhModal :open="modalOpen" title="Новый отдел" @close="modalOpen = false">
    <div style="display:flex;flex-direction:column;gap:12px">
      <p class="sm muted">Введите название — отдел появится в аналитике и выборе при управлении сотрудниками.</p>
      <input class="input" v-model="newDeptName" placeholder="Например: Аналитика"
        :style="deptError ? 'border-color:var(--sev-crit-text)' : ''"
        @keydown.enter="createDept" autofocus />
      <p v-if="deptError" class="xs" style="color:var(--sev-crit-text);margin-top:2px">{{ deptError }}</p>
    </div>
    <template #footer>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <PhButton variant="ghost" @click="modalOpen = false">Отмена</PhButton>
        <PhButton variant="primary" :disabled="!newDeptName.trim() || deptExists || saving" @click="createDept">
          {{ saving ? 'Создание…' : 'Создать' }}
        </PhButton>
      </div>
    </template>
  </PhModal>
</template>
