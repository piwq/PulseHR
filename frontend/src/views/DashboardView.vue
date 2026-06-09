<script setup>
import { ref, computed, onMounted } from 'vue'
import PhCard from '../components/ui/PhCard.vue'
import PhMetricCard from '../components/ui/PhMetricCard.vue'
import PhSeverityBadge from '../components/ui/PhSeverityBadge.vue'
import PhSkeleton from '../components/ui/PhSkeleton.vue'
import PhIcon from '../components/ui/PhIcon.vue'
import PhEmptyState from '../components/ui/PhEmptyState.vue'
import PhTrendChart from '../components/charts/PhTrendChart.vue'
import PhMultiSelect from '../components/ui/PhMultiSelect.vue'
import { api } from '../lib/api'
import { sevLabel } from '../lib/severity'

const data = ref(null)
const loading = ref(true)
const surveyId = ref(null)
const runId = ref(null)   // выбранная волна (null = активная/последняя с данными)

// ── Survey picker ──────────────────────────────────────────────────
const surveyMenuOpen = ref(false)
const surveySearch   = ref('')
const pickerMode     = ref('')
const pickerStatus   = ref('')

const MODE_OPTS   = [['', 'Все'], ['anonymous', 'Анонимный'], ['identified', 'Идентиф.']]
const STATUS_OPTS = [['', 'Все'], ['active', 'Активен'], ['completed', 'Завершён'], ['archive', 'Архив']]

const MODE_LABEL   = { anonymous: 'анонимный', identified: 'идентиф.' }
const STATUS_LABEL = { draft: 'черновик', active: 'активен', completed: 'завершён', archive: 'архив' }
const STATUS_CLS   = { active: 'badge--low' }

const currentSurvey = computed(() => (data.value?.surveys || []).find(s => String(s.id) === surveyId.value))

const visibleSurveys = computed(() => (data.value?.surveys || []).filter(s => {
  if (pickerMode.value   && s.mode   !== pickerMode.value)   return false
  if (pickerStatus.value && s.status !== pickerStatus.value) return false
  if (surveySearch.value) {
    const q = surveySearch.value.toLowerCase()
    if (!s.title.toLowerCase().includes(q)) return false
  }
  return true
}))

function openPicker()  { surveyMenuOpen.value = true; surveySearch.value = '' }
function closePicker() { surveyMenuOpen.value = false }

async function selectSurvey(id) {
  closePicker()
  if (String(id) === surveyId.value) return
  surveyId.value = String(id)
  runId.value = null   // новая серия → дефолтная волна
  await load()
}

// ── Волны (запуски) ────────────────────────────────────────────────
const runs = computed(() => data.value?.runs || [])
const currentRun = computed(() => data.value?.run || null)
const waveDelta = computed(() => data.value?.delta || null)
async function selectRun(e) {
  runId.value = e.target.value || null
  await load()
}
function runOptLabel(r) {
  const st = { active: 'активна', completed: 'завершена', archive: 'архив', draft: 'черновик' }[r.status] || r.status
  return `${r.label} · ${st} · ${r.responses} отв.`
}

// ── Data filters (affect chart + table) ────────────────────────────
const filterDepts = ref([])
const filterSev   = ref('')
const deptMenuOpen = ref(false)

// Серверные сегментные фильтры (город/должность) — пересегментируют анонимные ответы.
// Мультивыбор (как у отделов): пустой массив = «все».
const filterCity = ref([])
const filterJob  = ref([])
const cityOptions = computed(() => data.value?.filter_options?.cities || [])
const jobOptions  = computed(() => data.value?.filter_options?.job_titles || [])
async function applyServerFilter() { await load() }
function setCity(v) { filterCity.value = v; applyServerFilter() }
function setJob(v)  { filterJob.value = v;  applyServerFilter() }

const SEV_OPTS = [['', 'Все'], ['critical', 'Критично'], ['medium', 'Внимание'], ['low', 'Норма']]

const anyFilter = computed(() => filterDepts.value.length || filterSev.value || filterCity.value.length || filterJob.value.length)
function resetFilters() {
  filterDepts.value = []; filterSev.value = ''
  if (filterCity.value.length || filterJob.value.length) { filterCity.value = []; filterJob.value = []; load() }
}

// empty filterDepts = "all shown" (no filter active)
const isDeptChecked = (d) => filterDepts.value.length === 0 || filterDepts.value.includes(d)

function toggleDept(d) {
  if (filterDepts.value.length === 0) {
    // "all shown" → user unchecks one → select all except this one
    filterDepts.value = allDeptNames.value.filter(x => x !== d)
  } else {
    const i = filterDepts.value.indexOf(d)
    if (i >= 0) {
      filterDepts.value.splice(i, 1)
    } else {
      filterDepts.value.push(d)
      // if all are now explicitly selected → normalize back to "all shown"
      if (filterDepts.value.length === allDeptNames.value.length) filterDepts.value = []
    }
  }
}

function toggleAllDepts() {
  // "all shown" (empty) → select all explicitly so user can deselect some
  // any explicit selection → reset to "all shown"
  filterDepts.value = filterDepts.value.length === 0 ? [...allDeptNames.value] : []
}

async function load() {
  loading.value = true
  try {
    const p = new URLSearchParams()
    if (surveyId.value) p.set('id', surveyId.value)
    if (runId.value) p.set('run_id', runId.value)
    filterCity.value.forEach(c => p.append('city', c))
    filterJob.value.forEach(j => p.append('job_title', j))
    const qs = p.toString()
    const response = await api('/surveys/dashboard/' + (qs ? `?${qs}` : ''))
    // Set surveyId BEFORE data.value so the watch on filteredSurveys sees the correct id
    if (!surveyId.value && response?.survey) surveyId.value = String(response.survey.id)
    if (response?.run) runId.value = String(response.run.id)  // отразить выбранную волну в селекте
    data.value = response
  } finally {
    loading.value = false
  }
}

onMounted(load)

const VIZ = ['var(--viz-1)', 'var(--viz-2)', 'var(--viz-3)']

const allDeptNames = computed(() => [...new Set((data.value?.departments || []).map((d) => d.department).filter(Boolean))])

const depts = computed(() => {
  let list = (data.value?.departments || []).filter((d) => !d.suppressed)
  if (filterDepts.value.length) list = list.filter((d) => filterDepts.value.includes(d.department))
  if (filterSev.value) list = list.filter((d) => d.sev === filterSev.value)
  return list
})
const hasCritical = computed(() => depts.value.some((d) => d.sev === 'critical'))

// severity lookup for chart filtering
const sevMap = computed(() => Object.fromEntries(
  (data.value?.departments || []).map(d => [d.department, d.sev])
))

const series = computed(() => {
  const t = data.value?.trend
  if (!t) return []
  const out = [{ key: 'overall', label: 'Общая', color: 'var(--accent)', emphasis: true, values: t.overall }]
  const critName = depts.value.find((d) => d.sev === 'critical')?.department
  let vi = 0
  for (const d of t.departments) {
    if (filterDepts.value.length && !filterDepts.value.includes(d.department)) continue
    if (filterSev.value && sevMap.value[d.department] !== filterSev.value) continue
    const crit = d.department === critName
    out.push({
      key: d.department, label: d.department,
      color: crit ? 'var(--sev-crit)' : VIZ[vi++ % VIZ.length],
      emphasis: crit, crit, values: d.values,
    })
  }
  return out
})

// By-day chart
const byDay = computed(() => data.value?.by_day || [])
const maxDayCount = computed(() => Math.max(1, ...byDay.value.map((d) => d.count)))

// Distribution (top 3 questions)
const distribution = computed(() => (data.value?.distribution || []).slice(0, 3))

// Comments
const comments = computed(() => data.value?.comments || [])

function fmt(v, dec = 1) { return v == null ? '—' : Number(v).toFixed(dec) }

function distMax(q) {
  return Math.max(1, ...Object.values(q.options || {}))
}
</script>

<template>
  <div v-if="loading" style="display:flex;flex-direction:column;gap:16px">
    <div class="kpi-row">
      <PhCard v-for="i in 3" :key="i"><PhSkeleton w="55%" :h="13" /><PhSkeleton w="40%" :h="32" :style="{ marginTop: '14px' }" /></PhCard>
    </div>
    <PhCard><PhSkeleton w="40%" :h="16" /><PhSkeleton w="100%" :h="200" :style="{ marginTop: '18px' }" /></PhCard>
  </div>

  <div v-else-if="data" class="route" style="display:flex;flex-direction:column;gap:16px" @click="deptMenuOpen = false; closePicker()">

    <!-- Survey picker + data filters -->
    <div v-if="data.surveys?.length" style="display:flex;flex-direction:column;gap:10px">

      <!-- Кастомный survey picker -->
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <span class="sm muted" style="flex:none">Опрос:</span>
        <div class="sp-wrap" @click.stop>
          <!-- Триггер -->
          <button class="sp-trigger" :class="surveyMenuOpen && 'sp-trigger--open'" @click="surveyMenuOpen ? closePicker() : openPicker()">
            <span class="sp-trigger__name">{{ currentSurvey?.title ?? '—' }}</span>
            <div class="sp-trigger__meta">
              <span v-if="currentSurvey" class="badge" :class="STATUS_CLS[currentSurvey.status] || 'badge--neutral'">
                <span class="badge__dot" />{{ STATUS_LABEL[currentSurvey.status] }}
              </span>
              <span v-if="currentSurvey" class="xs muted">{{ MODE_LABEL[currentSurvey.mode] }}</span>
            </div>
            <PhIcon name="down" :size="12" style="flex:none;color:var(--text-muted);transition:transform .15s" :style="surveyMenuOpen ? 'transform:rotate(180deg)' : ''" />
          </button>

          <!-- Дропдаун -->
          <div v-if="surveyMenuOpen" class="sp-menu">
            <!-- Поиск -->
            <div class="sp-search">
              <PhIcon name="search" :size="13" style="color:var(--text-muted);flex:none" />
              <input v-model="surveySearch" class="sp-search__input" placeholder="Поиск по названию…" autofocus />
            </div>
            <!-- Фильтры режима и статуса -->
            <div class="sp-filters">
              <div class="seg">
                <button v-for="[v, l] in MODE_OPTS" :key="v"
                  class="seg__btn" :class="pickerMode === v && 'seg__btn--on'"
                  @click="pickerMode = v">{{ l }}</button>
              </div>
              <div class="seg">
                <button v-for="[v, l] in STATUS_OPTS" :key="v"
                  class="seg__btn" :class="pickerStatus === v && 'seg__btn--on'"
                  @click="pickerStatus = v">{{ l }}</button>
              </div>
            </div>
            <div class="sp-divider" />
            <!-- Список опросов -->
            <div class="sp-list">
              <div v-if="!visibleSurveys.length" class="sp-empty">Ничего не найдено</div>
              <div v-for="s in visibleSurveys" :key="s.id"
                class="sp-item" :class="String(s.id) === surveyId && 'sp-item--active'"
                @click="selectSurvey(s.id)">
                <div class="sp-item__check">
                  <PhIcon v-if="String(s.id) === surveyId" name="check" :size="12" />
                </div>
                <div class="sp-item__body">
                  <div class="sp-item__title">{{ s.title }}</div>
                  <div class="sp-item__meta">
                    <span class="badge badge--neutral" style="font-size:10px;padding:1px 5px">{{ MODE_LABEL[s.mode] }}</span>
                    <span class="badge" :class="STATUS_CLS[s.status] || 'badge--neutral'" style="font-size:10px;padding:1px 5px">
                      <span class="badge__dot" />{{ STATUS_LABEL[s.status] }}
                    </span>
                  </div>
                </div>
                <span class="sp-item__count">{{ s.response_count }} отв.</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Строка данных: волна + отдел + сигнал (влияют на график и таблицу) -->
      <div class="filter-bar">
        <select v-if="runs.length" class="select select--sm" :value="currentRun?.id" @change="selectRun">
          <option v-for="r in runs" :key="r.id" :value="r.id">{{ runOptLabel(r) }}</option>
        </select>
        <div v-if="runs.length" class="filter-bar__sep" />
        <div style="position:relative" @click.stop>
          <button class="dept-btn" :class="filterDepts.length && 'dept-btn--active'"
            @click="deptMenuOpen = !deptMenuOpen">
            {{ filterDepts.length ? filterDepts.length + ' отд.' : 'Все отделы' }}
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 3.5l3 3 3-3"/></svg>
          </button>
          <div v-if="deptMenuOpen" class="dept-menu">
            <div class="dept-toggle-all" @click="toggleAllDepts">
              <input type="checkbox" :checked="filterDepts.length === 0" :indeterminate="filterDepts.length > 0 && filterDepts.length < allDeptNames.length" readonly />
              <span>{{ filterDepts.length === 0 ? 'Все отделы' : 'Снять выбор' }}</span>
            </div>
            <div class="dept-sep" />
            <label v-for="d in allDeptNames" :key="d" class="dept-item">
              <input type="checkbox" :checked="isDeptChecked(d)" @change="toggleDept(d)" />
              <span>{{ d }}</span>
            </label>
          </div>
        </div>
        <div class="filter-bar__sep" />
        <div class="seg">
          <button v-for="[v, l] in SEV_OPTS" :key="v"
            class="seg__btn" :class="filterSev === v && 'seg__btn--on'"
            @click="filterSev = v">{{ l }}</button>
        </div>
        <template v-if="cityOptions.length">
          <div class="filter-bar__sep" />
          <PhMultiSelect :model-value="filterCity" :options="cityOptions" all-label="Все города"
            @update:model-value="setCity" />
        </template>
        <PhMultiSelect v-if="jobOptions.length" :model-value="filterJob" :options="jobOptions"
          all-label="Все должности" @update:model-value="setJob" />
        <button v-if="anyFilter" class="filter-reset" @click="resetFilters">× сбросить</button>
      </div>
    </div>

    <!-- Нет данных по выбранному опросу -->
    <PhCard v-if="!data?.survey">
      <PhEmptyState icon="survey" title="Нет ответов"
        body="По этому опросу ещё нет ответов. Выберите другой или дождитесь прохождений." />
    </PhCard>

    <!-- Аналитика (только когда есть данные) -->
    <template v-if="data?.survey">

    <!-- KPI -->
    <div class="kpi-row">
      <PhMetricCard
        label="Индекс вовлечённости" scale-hint="/ 5"
        hint="Средний балл по всем шкальным вопросам опроса (1–5). Ниже 3.5 — сигнал тревоги, ниже 3.0 — критично."
        :to="data.kpis.engagement ?? 0" :dec="1"
        :delta-dir="(waveDelta?.engagement ?? 0) >= 0 ? 'up' : 'down'"
        :delta-text="waveDelta?.engagement != null ? `${waveDelta.engagement > 0 ? '+' : ''}${waveDelta.engagement} к ${waveDelta.prev_label}` : undefined" />
      <PhMetricCard
        label="eNPS" scale-hint="−100…100"
        hint="Employee Net Promoter Score: % промоутеров (9–10 баллов) минус % критиков (0–6 баллов). Выше 0 — хорошо, выше +30 — отлично."
        :to="data.kpis.enps ?? 0" plus
        :delta-dir="(waveDelta?.enps ?? 0) >= 0 ? 'up' : 'down'"
        :delta-text="waveDelta?.enps != null ? `${waveDelta.enps > 0 ? '+' : ''}${waveDelta.enps} к ${waveDelta.prev_label}` : undefined" />
      <PhMetricCard
        label="Участие в опросе" unit="%"
        hint="Доля сотрудников из целевой аудитории, завершивших опрос. Ниже 60% — низкая репрезентативность данных."
        :to="data.kpis.participation ?? 0"
        :delta-dir="(waveDelta?.participation ?? 0) >= 0 ? 'up' : 'down'"
        :delta-text="waveDelta?.participation != null ? `${waveDelta.participation > 0 ? '+' : ''}${waveDelta.participation}% к ${waveDelta.prev_label}` : undefined" />
    </div>

    <!-- Тренд вовлечённости -->
    <PhCard :pad="false">
      <div class="chart-card">
        <div class="chart-head">
          <div>
            <div class="h3" style="font-size:16px">Динамика вовлечённости по отделам</div>
            <div class="xs muted" style="margin-top:2px">{{ data.survey.title }} · шкала 1–5</div>
          </div>
          <div class="legend">
            <span v-for="s in series" :key="s.key"><i :style="{ background: s.color }" />{{ s.label }}</span>
          </div>
        </div>
        <PhTrendChart v-if="series.length" :series="series" :labels="data.trend.labels" />
        <div v-if="hasCritical" style="display:flex;gap:8px;align-items:center;margin-top:8px;padding:10px 12px;border-radius:var(--r-md);background:var(--sev-crit-soft);border:1px solid oklch(0.64 0.165 25 / 0.22)">
          <PhIcon name="alert" :size="15" style="color:var(--sev-crit-text);flex:none" />
          <span class="sm" style="color:var(--text-secondary)">Есть отделы с критическим сигналом — откройте раздел «Алерты».</span>
        </div>
      </div>
    </PhCard>

    <!-- По дням -->
    <PhCard v-if="byDay.length" :pad="false">
      <div class="chart-card">
        <div class="h3" style="font-size:15px;margin-bottom:14px">Прохождения по дням</div>
        <div class="by-day">
          <div v-for="d in byDay" :key="d.date" class="by-day__col">
            <div class="by-day__count">{{ d.count }}</div>
            <div class="by-day__bar">
              <div class="by-day__fill" :style="{ height: Math.max(4, Math.round(d.count / maxDayCount * 80)) + 'px' }" />
            </div>
            <div class="by-day__label">{{ d.date.slice(5) }}</div>
          </div>
        </div>
      </div>
    </PhCard>

    <!-- Распределение ответов -->
    <PhCard v-if="distribution.length" :pad="false">
      <div style="padding:14px 16px 16px">
        <div class="h3" style="font-size:15px;margin-bottom:14px">Распределение ответов</div>
        <div v-for="q in distribution" :key="q.question" style="margin-bottom:18px">
          <div class="sm" style="font-weight:600;margin-bottom:8px">{{ q.question }}</div>
          <div v-for="(cnt, opt) in q.options" :key="opt" style="display:flex;align-items:center;gap:10px;margin-bottom:5px">
            <div class="xs muted" style="width:120px;flex:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" :title="opt">{{ opt }}</div>
            <div style="flex:1;height:10px;background:var(--bg-raised);border-radius:99px;overflow:hidden">
              <div :style="{ width: Math.round(cnt / distMax(q) * 100) + '%', height: '100%', background: 'var(--accent)', borderRadius: '99px', transition: 'width .4s var(--ease)' }" />
            </div>
            <div class="xs tnum muted" style="width:28px;text-align:right;flex:none">{{ cnt }}</div>
          </div>
        </div>
      </div>
    </PhCard>

    <!-- Сигналы по отделам -->
    <PhCard :pad="false">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 16px 10px">
        <div class="h3" style="font-size:15px">Сигналы по отделам</div>
        <div class="xs muted">{{ data.kpis.responses }} ответов</div>
      </div>
      <table class="tbl">
        <thead><tr><th>Отдел</th><th>Вовл.</th><th>eNPS</th><th>Участие</th><th>Причина</th><th style="text-align:right">Статус</th></tr></thead>
        <tbody>
          <tr v-for="d in depts" :key="d.department">
            <td style="font-weight:600">{{ d.department }}</td>
            <td class="num tnum">{{ fmt(d.eng) }}</td>
            <td class="num tnum" :style="{ color: (d.enps ?? 0) < 0 ? 'var(--sev-crit-text)' : 'var(--text-secondary)' }">{{ d.enps == null ? '—' : (d.enps > 0 ? '+' : '') + d.enps }}</td>
            <td class="num tnum">{{ d.part == null ? '—' : d.part + '%' }}</td>
            <td class="muted">{{ d.note }}</td>
            <td style="text-align:right"><PhSeverityBadge :level="d.sev" pulse>{{ sevLabel(d.sev) }}</PhSeverityBadge></td>
          </tr>
        </tbody>
      </table>
    </PhCard>

    <!-- Комментарии -->
    <PhCard v-if="comments.length">
      <div class="h3" style="font-size:15px;margin-bottom:12px">Комментарии сотрудников</div>
      <div v-for="(c, i) in comments" :key="i" class="comment-row">
        <PhIcon name="quote" :size="14" style="color:var(--accent);flex:none;margin-top:2px" />
        <span class="sm">{{ c }}</span>
      </div>
    </PhCard>

    </template><!-- /v-if data.survey -->

  </div>
</template>

<style scoped>
/* ── Survey picker ──────────────────────────────────────────────── */
.sp-wrap { position: relative; }

.sp-trigger {
  display: inline-flex; align-items: center; gap: 8px;
  background: var(--bg-sunken); border: 1px solid var(--line-strong);
  border-radius: 10px; padding: 7px 12px; cursor: pointer;
  font-family: inherit; max-width: 420px; min-width: 220px;
  transition: border-color .12s;
}
.sp-trigger:hover, .sp-trigger--open { border-color: var(--accent); }
.sp-trigger__name {
  font-size: 13px; font-weight: 600; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; min-width: 0;
}
.sp-trigger__meta { display: flex; align-items: center; gap: 5px; flex: none; }

.sp-menu {
  position: absolute; top: calc(100% + 6px); left: 0; z-index: 400;
  background: var(--bg-base); border: 1px solid var(--line-strong);
  border-radius: 12px; box-shadow: 0 12px 32px rgba(0,0,0,.4);
  width: 360px; overflow: hidden;
}
.sp-search {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; border-bottom: 1px solid var(--line);
}
.sp-search__input {
  flex: 1; background: none; border: none; outline: none;
  font-family: inherit; font-size: 13px; color: var(--text);
}
.sp-search__input::placeholder { color: var(--text-faint); }
.sp-filters {
  display: flex; gap: 6px; padding: 8px 10px; flex-wrap: wrap;
  border-bottom: 1px solid var(--line); background: var(--bg-sunken);
}
.sp-divider { height: 1px; background: var(--line); }
.sp-list { max-height: 260px; overflow-y: auto; padding: 4px 0; }
.sp-empty { padding: 16px 14px; font-size: 12px; color: var(--text-muted); text-align: center; }

.sp-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; cursor: pointer; transition: background .1s;
}
.sp-item:hover { background: var(--bg-raised); }
.sp-item--active { background: var(--accent-soft); }
.sp-item__check { width: 16px; flex: none; color: var(--accent); }
.sp-item__body { flex: 1; min-width: 0; }
.sp-item__title { font-size: 13px; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sp-item__meta { display: flex; gap: 4px; margin-top: 3px; }
.sp-item__count { font-size: 11px; color: var(--text-muted); flex: none; white-space: nowrap; }

/* ── Filter bar ─────────────────────────────────────────────────── */
.filter-bar {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
}
.filter-bar__sep {
  width: 1px; height: 18px; background: var(--line); flex: none;
}
.select--sm {
  height: 30px; padding: 0 26px 0 10px; font-size: 12px;
  border-radius: 8px; min-width: 120px;
}

/* Segmented control */
.seg {
  display: flex; background: var(--bg-sunken);
  border-radius: 8px; padding: 3px; gap: 2px;
}
.seg__btn {
  font-size: 11px; line-height: 1; padding: 4px 10px;
  border-radius: 5px; border: none; background: none;
  cursor: pointer; color: var(--text-secondary);
  font-family: inherit; white-space: nowrap;
  transition: color .12s;
}
.seg__btn:hover { color: var(--text); }
.seg__btn--on {
  background: var(--bg-base); color: var(--text);
  box-shadow: 0 1px 3px rgba(0,0,0,.22);
}

/* Department multi-select */
.dept-btn {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; font-family: inherit;
  background: var(--bg-sunken); color: var(--text-secondary);
  border: 1px solid var(--line-strong); border-radius: 8px;
  padding: 4px 10px; cursor: pointer; white-space: nowrap;
  transition: color .12s, border-color .12s;
}
.dept-btn:hover { border-color: var(--text-faint); color: var(--text); }
.dept-btn--active { color: var(--accent-text); border-color: var(--accent); background: var(--accent-soft); }

.dept-menu {
  position: absolute; top: calc(100% + 5px); left: 0; z-index: 300;
  background: var(--bg-base); border: 1px solid var(--line-strong);
  border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,.35);
  min-width: 160px; padding: 6px 0; overflow: hidden;
}
.dept-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px; cursor: pointer; font-size: 12px; color: var(--text);
  transition: background .1s;
}
.dept-item:hover { background: var(--bg-raised); }
.dept-item input[type=checkbox] { accent-color: var(--accent); width: 13px; height: 13px; flex: none; }
.dept-toggle-all {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px; cursor: pointer; font-size: 12px;
  font-weight: 600; color: var(--text-secondary);
  transition: background .1s;
}
.dept-toggle-all:hover { background: var(--bg-raised); }
.dept-toggle-all input[type=checkbox] { accent-color: var(--accent); width: 13px; height: 13px; flex: none; pointer-events: none; }
.dept-sep { height: 1px; background: var(--line); margin: 2px 0; }
.dept-clear {
  margin: 4px 8px 2px; padding: 4px 8px; font-size: 11px; color: var(--text-muted);
  cursor: pointer; border-radius: 5px; text-align: center;
  border-top: 1px solid var(--line);
}
.dept-clear:hover { color: var(--text-secondary); background: var(--bg-raised); }

/* Reset link */
.filter-reset {
  font-size: 11px; background: none; border: none;
  cursor: pointer; color: var(--text-muted); padding: 4px 8px;
  border-radius: 6px; font-family: inherit;
}
.filter-reset:hover { color: var(--text-secondary); background: var(--bg-sunken); }

/* ── Charts ─────────────────────────────────────────────────────── */
.by-day { display: flex; align-items: flex-end; gap: 6px; overflow-x: auto; padding-bottom: 2px; }
.by-day__col { display: flex; flex-direction: column; align-items: center; gap: 4px; min-width: 32px; }
.by-day__count { font-size: 10px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.by-day__bar { display: flex; align-items: flex-end; height: 80px; }
.by-day__fill { width: 18px; background: var(--accent); border-radius: 3px 3px 0 0; min-height: 4px; transition: height .4s var(--ease); }
.by-day__label { font-size: 9px; color: var(--text-faint); font-variant-numeric: tabular-nums; white-space: nowrap; }
.comment-row { display: flex; gap: 8px; padding: 7px 0; border-bottom: 1px solid var(--line); }
.comment-row:last-child { border-bottom: none; }
</style>
