<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import PhCard from '../components/ui/PhCard.vue'
import PhEmptyState from '../components/ui/PhEmptyState.vue'
import { api } from '../lib/api'

const surveys = ref([])
const surveyId = ref('')
const data = ref(null)
const loading = ref(false)

onMounted(async () => {
  const list = await api('/surveys/')
  // только опросы, которые запускались (есть волны)
  surveys.value = list.filter(s => s.run_count > 0)
  const multi = surveys.value.find(s => s.run_count > 1) || surveys.value[0]
  if (multi) surveyId.value = String(multi.id)
})

watch(surveyId, async (id) => {
  if (!id) { data.value = null; return }
  loading.value = true
  try { data.value = await api(`/surveys/${id}/comparison/`) }
  finally { loading.value = false }
})

const runs = computed(() => data.value?.runs || [])
const labels = computed(() => data.value?.labels || [])
const departments = computed(() => data.value?.departments || [])

// цвет ячейки вовлечённости (1–5): красный → жёлтый → зелёный
function engColor(v) {
  if (v == null) return 'transparent'
  const t = Math.max(0, Math.min(1, (v - 2.5) / 2))  // 2.5→0, 4.5→1
  const hue = Math.round(t * 120)                      // 0 красный … 120 зелёный
  return `hsl(${hue} 60% 28%)`
}
// дельта между последней и первой непустой волной отдела
function deptTrend(values) {
  const v = values.filter(x => x != null)
  if (v.length < 2) return null
  return Math.round((v[v.length - 1] - v[0]) * 100) / 100
}
function kpiDelta(arr, i, key) {
  if (i === 0) return null
  const a = arr[i][key], b = arr[i - 1][key]
  if (a == null || b == null) return null
  return Math.round((a - b) * 100) / 100
}
function fmt(v, plus = false) {
  if (v == null) return '—'
  return (plus && v > 0 ? '+' : '') + v
}
</script>

<template>
  <div class="route" style="display:flex;flex-direction:column;gap:14px">
    <PhCard :pad="false">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 18px">
        <div>
          <div class="h3" style="font-size:15px">Сравнение волн опроса</div>
          <div class="xs muted" style="margin-top:2px">Динамика KPI по запускам и вовлечённость отделов от волны к волне</div>
        </div>
        <select class="select" v-model="surveyId" style="min-width:240px">
          <option v-for="s in surveys" :key="s.id" :value="String(s.id)">{{ s.title }} ({{ s.run_count }} волн)</option>
        </select>
      </div>
    </PhCard>

    <PhCard v-if="!surveyId || runs.length < 1">
      <PhEmptyState icon="trend" title="Нет данных для сравнения"
        body="Опрос ещё не запускался или нет ответов. Запустите опрос (волну) на странице «Опросы»." />
    </PhCard>

    <template v-else>
      <!-- KPI по волнам -->
      <PhCard :pad="false">
        <table class="cmp">
          <thead>
            <tr>
              <th>Метрика</th>
              <th v-for="(r, i) in runs" :key="r.run_id">
                {{ r.label }}
                <span class="st" :class="'st--' + r.status">{{ r.status === 'active' ? 'активна' : 'завершена' }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="metric">Вовлечённость <span class="muted xs">/ 5</span></td>
              <td v-for="(r, i) in runs" :key="r.run_id">
                <span class="val">{{ fmt(r.engagement) }}</span>
                <span v-if="kpiDelta(runs, i, 'engagement') != null"
                  class="d" :class="kpiDelta(runs, i, 'engagement') >= 0 ? 'up' : 'down'">
                  {{ fmt(kpiDelta(runs, i, 'engagement'), true) }}
                </span>
              </td>
            </tr>
            <tr>
              <td class="metric">eNPS</td>
              <td v-for="(r, i) in runs" :key="r.run_id">
                <span class="val">{{ fmt(r.enps) }}</span>
                <span v-if="kpiDelta(runs, i, 'enps') != null"
                  class="d" :class="kpiDelta(runs, i, 'enps') >= 0 ? 'up' : 'down'">
                  {{ fmt(kpiDelta(runs, i, 'enps'), true) }}
                </span>
              </td>
            </tr>
            <tr>
              <td class="metric">Участие <span class="muted xs">%</span></td>
              <td v-for="(r, i) in runs" :key="r.run_id">
                <span class="val">{{ fmt(r.participation) }}</span>
                <span v-if="kpiDelta(runs, i, 'participation') != null"
                  class="d" :class="kpiDelta(runs, i, 'participation') >= 0 ? 'up' : 'down'">
                  {{ fmt(kpiDelta(runs, i, 'participation'), true) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </PhCard>

      <!-- Вовлечённость по отделам × волнам (heatmap) -->
      <PhCard :pad="false">
        <div style="padding:12px 18px 0"><div class="h3" style="font-size:14px">Вовлечённость по отделам</div>
          <div class="xs muted" style="margin-top:2px">Цвет — уровень (1–5). Отделы с n&lt;5 в волне скрыты (анонимность).</div></div>
        <table class="cmp" style="margin-top:10px">
          <thead>
            <tr><th>Отдел</th><th v-for="l in labels" :key="l">{{ l }}</th><th>Тренд</th></tr>
          </thead>
          <tbody>
            <tr v-for="dep in departments" :key="dep.department">
              <td class="metric">{{ dep.department }}</td>
              <td v-for="(v, i) in dep.values" :key="i" class="heat">
                <span class="cell" :style="{ background: engColor(v) }">{{ v == null ? '—' : v }}</span>
              </td>
              <td>
                <span v-if="deptTrend(dep.values) != null" class="d" :class="deptTrend(dep.values) >= 0 ? 'up' : 'down'">
                  {{ fmt(deptTrend(dep.values), true) }}
                </span>
                <span v-else class="muted">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </PhCard>
    </template>
  </div>
</template>

<style scoped>
.cmp { width: 100%; border-collapse: collapse; font-size: 13px; }
.cmp th {
  text-align: left; padding: 10px 14px; font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: .04em; color: var(--text-muted);
  border-bottom: 1px solid var(--line);
}
.cmp td { padding: 11px 14px; border-bottom: 1px solid var(--line); color: var(--text); }
.cmp tr:last-child td { border-bottom: none; }
.metric { font-weight: 600; }
.val { font-variant-numeric: tabular-nums; }
.d { margin-left: 8px; font-size: 12px; font-weight: 600; font-variant-numeric: tabular-nums; }
.d.up { color: #4ade80; }
.d.down { color: var(--sev-crit-text); }
.heat { text-align: center; }
.cell {
  display: inline-block; min-width: 38px; padding: 4px 8px; border-radius: 6px;
  color: #fff; font-variant-numeric: tabular-nums; font-weight: 600;
}
.st { margin-left: 6px; font-size: 10px; font-weight: 600; text-transform: none; letter-spacing: 0; }
.st--active { color: #4ade80; }
.st--completed { color: var(--text-muted); }
</style>
