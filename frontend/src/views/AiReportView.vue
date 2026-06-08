<script setup>
import { ref, computed, onMounted } from 'vue'
import PhCard from '../components/ui/PhCard.vue'
import PhButton from '../components/ui/PhButton.vue'
import PhIcon from '../components/ui/PhIcon.vue'
import PhSkeleton from '../components/ui/PhSkeleton.vue'
import PhEmptyState from '../components/ui/PhEmptyState.vue'
import { api } from '../lib/api'
import { useToasts } from '../stores/useToasts'

const toasts = useToasts()

const surveys      = ref([])
const minResponses = ref(10)
const loading      = ref(true)
const surveyId     = ref(null)
const reports      = ref([])       // все версии, новые первыми
const versionIdx   = ref(0)        // какая версия показана (0 = последняя)
const generating   = ref(false)

// ── Survey picker ──────────────────────────────────────────────────
const menuOpen = ref(false)
const search   = ref('')
const fMode    = ref('')
const fStatus  = ref('')

const MODE_OPTS   = [['', 'Все'], ['anonymous', 'Анонимный'], ['identified', 'Идентиф.']]
const STATUS_OPTS = [['', 'Все'], ['active', 'Активен'], ['completed', 'Завершён'], ['archive', 'Архив']]
const MODE_LABEL   = { anonymous: 'анонимный', identified: 'идентиф.' }
const STATUS_LABEL = { draft: 'черновик', active: 'активен', completed: 'завершён', archive: 'архив' }
const STATUS_CLS   = { active: 'badge--low' }

const currentSurvey = computed(() => surveys.value.find(s => String(s.id) === surveyId.value))

const visibleSurveys = computed(() => surveys.value.filter(s => {
  if (fMode.value   && s.mode   !== fMode.value)   return false
  if (fStatus.value && s.status !== fStatus.value) return false
  if (search.value && !s.title.toLowerCase().includes(search.value.toLowerCase())) return false
  return true
}))

function openMenu()  { menuOpen.value = true; search.value = '' }
function closeMenu() { menuOpen.value = false }

async function selectSurvey(id) {
  closeMenu()
  if (String(id) === surveyId.value) return
  surveyId.value = String(id)
  await loadReports()
}

// ── Версии отчёта ──────────────────────────────────────────────────
const current      = computed(() => reports.value[versionIdx.value] || null)
const olderVersion = computed(() => reports.value[versionIdx.value + 1] || null)
const isArchived   = computed(() => versionIdx.value > 0)

const KPI_DEFS = [
  { key: 'engagement',   label: 'Вовлечённость', suffix: '',  better: 'up' },
  { key: 'enps',         label: 'eNPS',          suffix: '',  better: 'up' },
  { key: 'participation',label: 'Участие',       suffix: '%', better: 'up' },
  { key: 'responses',    label: 'Ответов',       suffix: '',  better: 'neutral' },
]

function kpiVal(k) {
  const v = current.value?.kpis?.[k]
  return v == null ? '—' : v
}
function kpiDelta(k) {
  const a = current.value?.kpis?.[k]
  const b = olderVersion.value?.kpis?.[k]
  if (a == null || b == null) return null
  return Math.round((a - b) * 100) / 100
}

// ── Data ───────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const res = await api('/insights/report-surveys/')
    surveys.value = res?.surveys || []
    minResponses.value = res?.min_responses ?? 10
    if (surveys.value.length) {
      surveyId.value = String(surveys.value[0].id)
      await loadReports()
    }
  } catch {
    toasts.push({ tone: 'critical', badge: 'Ошибка', title: 'Не удалось загрузить опросы' })
  } finally {
    loading.value = false
  }
})

async function loadReports() {
  reports.value = []
  versionIdx.value = 0
  try {
    const res = await api(`/insights/report/${surveyId.value}/`)
    reports.value = res?.reports || []
  } catch { /* нет отчётов — покажем пустое состояние */ }
}

async function generate() {
  if (!surveyId.value || generating.value) return
  generating.value = true
  try {
    const res = await api(`/insights/report/${surveyId.value}/generate/`, { method: 'POST' })
    if (res?.report) { reports.value = [res.report, ...reports.value]; versionIdx.value = 0 }
  } catch (e) {
    toasts.push({
      tone: 'critical', badge: 'Ошибка',
      title: 'Не удалось сгенерировать отчёт',
      body: e?.data?.detail || 'Попробуйте ещё раз.',
    })
  } finally {
    generating.value = false
  }
}

const SECTIONS = [
  { key: 'overall',         title: 'Общая оценка',               icon: 'grid',   list: false },
  { key: 'problem_zones',   title: 'Проблемные зоны',            icon: 'alert',  list: true  },
  { key: 'survey_quality',  title: 'Качество составления опроса', icon: 'survey', list: false },
  { key: 'recommendations', title: 'Рекомендации',               icon: 'check',  list: true  },
]

function fmtDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}
</script>

<template>
  <!-- Загрузка списка опросов -->
  <div v-if="loading" style="display:flex;flex-direction:column;gap:16px">
    <PhCard><PhSkeleton w="40%" :h="14" /></PhCard>
    <PhCard><PhSkeleton w="55%" :h="16" /><PhSkeleton w="100%" :h="80" :style="{ marginTop: '14px' }" /></PhCard>
  </div>

  <PhCard v-else-if="!surveys.length">
    <PhEmptyState icon="survey" title="Нет подходящих опросов"
      :body="`ИИ-отчёт доступен для опросов с числом ответов ≥ ${minResponses}. Пока таких нет.`" />
  </PhCard>

  <div v-else class="route" style="display:flex;flex-direction:column;gap:16px" @click="closeMenu">

    <!-- Survey picker -->
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      <span class="sm muted" style="flex:none">Опрос:</span>
      <div class="sp-wrap" @click.stop>
        <button class="sp-trigger" :class="menuOpen && 'sp-trigger--open'" @click="menuOpen ? closeMenu() : openMenu()">
          <span class="sp-trigger__name">{{ currentSurvey?.title ?? '—' }}</span>
          <div class="sp-trigger__meta">
            <span v-if="currentSurvey" class="badge" :class="STATUS_CLS[currentSurvey.status] || 'badge--neutral'">
              <span class="badge__dot" />{{ STATUS_LABEL[currentSurvey.status] }}
            </span>
            <span v-if="currentSurvey" class="xs muted">{{ MODE_LABEL[currentSurvey.mode] }}</span>
          </div>
          <PhIcon name="down" :size="12" style="flex:none;color:var(--text-muted);transition:transform .15s" :style="menuOpen ? 'transform:rotate(180deg)' : ''" />
        </button>

        <div v-if="menuOpen" class="sp-menu">
          <div class="sp-search">
            <PhIcon name="search" :size="13" style="color:var(--text-muted);flex:none" />
            <input v-model="search" class="sp-search__input" placeholder="Поиск по названию…" autofocus />
          </div>
          <div class="sp-filters">
            <div class="seg">
              <button v-for="[v, l] in MODE_OPTS" :key="v" class="seg__btn" :class="fMode === v && 'seg__btn--on'" @click="fMode = v">{{ l }}</button>
            </div>
            <div class="seg">
              <button v-for="[v, l] in STATUS_OPTS" :key="v" class="seg__btn" :class="fStatus === v && 'seg__btn--on'" @click="fStatus = v">{{ l }}</button>
            </div>
          </div>
          <div class="sp-divider" />
          <div class="sp-list">
            <div v-if="!visibleSurveys.length" class="sp-empty">Ничего не найдено</div>
            <div v-for="s in visibleSurveys" :key="s.id" class="sp-item" :class="String(s.id) === surveyId && 'sp-item--active'" @click="selectSurvey(s.id)">
              <div class="sp-item__check"><PhIcon v-if="String(s.id) === surveyId" name="check" :size="12" /></div>
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

    <!-- Генерация в процессе -->
    <PhCard v-if="generating" :pad="false">
      <div class="gen-state">
        <div class="gen-spinner"><PhIcon name="spark" :size="22" /></div>
        <div>
          <div class="h3" style="font-size:15px">ИИ анализирует опрос…</div>
          <div class="xs muted" style="margin-top:3px">Обычно занимает 2–10 секунд</div>
        </div>
      </div>
      <div style="padding:0 18px 18px;display:flex;flex-direction:column;gap:10px">
        <PhSkeleton w="100%" :h="60" />
        <PhSkeleton w="100%" :h="60" />
      </div>
    </PhCard>

    <!-- Нет отчёта -->
    <PhCard v-else-if="!reports.length">
      <PhEmptyState icon="spark" title="Отчёт ещё не создан"
        body="Сформируйте краткую ИИ-сводку по выбранному опросу: проблемные метрики, отделы и рекомендации.">
        <template #action>
          <PhButton variant="primary" icon="spark" @click="generate">Сгенерировать отчёт</PhButton>
        </template>
      </PhEmptyState>
    </PhCard>

    <!-- Отчёт -->
    <template v-else>
      <div class="report-meta">
        <div class="ver-nav">
          <button class="ver-btn" :disabled="versionIdx >= reports.length - 1" @click="versionIdx++" title="Предыдущая версия">
            <svg width="9" height="9" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M6.5 2L3 5l3.5 3"/></svg>
          </button>
          <span class="ver-label">
            Версия {{ reports.length - versionIdx }} из {{ reports.length }}
            <span class="xs muted">· {{ fmtDate(current.created_at) }}</span>
          </span>
          <button class="ver-btn" :disabled="versionIdx <= 0" @click="versionIdx--" title="Следующая версия">
            <svg width="9" height="9" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3.5 2L7 5l-3.5 3"/></svg>
          </button>
          <span v-if="isArchived" class="badge badge--neutral" style="font-size:10px">архивная</span>
          <span class="xs muted" style="margin-left:2px">{{ current.model_used || '—' }}</span>
        </div>
        <PhButton variant="secondary" icon="refresh" @click="generate">Перегенерировать</PhButton>
      </div>

      <!-- Сравнение метрик с предыдущей версией -->
      <PhCard v-if="olderVersion" :pad="false">
        <div style="padding:12px 16px">
          <div class="xs muted" style="margin-bottom:10px">Изменения метрик относительно предыдущей версии</div>
          <div class="kpi-deltas">
            <div v-for="d in KPI_DEFS" :key="d.key" class="kpi-delta">
              <div class="kpi-delta__label">{{ d.label }}</div>
              <div class="kpi-delta__val">{{ kpiVal(d.key) }}<span v-if="kpiVal(d.key) !== '—'" class="kpi-delta__suf">{{ d.suffix }}</span></div>
              <div v-if="kpiDelta(d.key) !== null && kpiDelta(d.key) !== 0" class="kpi-delta__chg"
                :class="d.better === 'neutral' ? 'chg-neutral' : (kpiDelta(d.key) > 0 ? 'chg-up' : 'chg-down')">
                {{ kpiDelta(d.key) > 0 ? '▲ +' : '▼ ' }}{{ kpiDelta(d.key) }}
              </div>
              <div v-else class="kpi-delta__chg chg-flat">без изменений</div>
            </div>
          </div>
        </div>
      </PhCard>

      <PhCard v-for="sec in SECTIONS" :key="sec.key">
        <div class="sec-head">
          <PhIcon :name="sec.icon" :size="15" style="color:var(--accent)" />
          <span class="h3" style="font-size:15px">{{ sec.title }}</span>
        </div>
        <ul v-if="sec.list" class="sec-list">
          <li v-for="(item, i) in (current.content[sec.key] || [])" :key="i">{{ item }}</li>
          <li v-if="!(current.content[sec.key] || []).length" class="muted">—</li>
        </ul>
        <p v-else class="sec-text">{{ current.content[sec.key] || '—' }}</p>
      </PhCard>
    </template>

  </div>
</template>

<style scoped>
/* ── Survey picker (как в DashboardView) ──────────────────────────── */
.sp-wrap { position: relative; }
.sp-trigger {
  display: inline-flex; align-items: center; gap: 8px;
  background: var(--bg-sunken); border: 1px solid var(--line-strong);
  border-radius: 10px; padding: 7px 12px; cursor: pointer;
  font-family: inherit; max-width: 420px; min-width: 220px; transition: border-color .12s;
}
.sp-trigger:hover, .sp-trigger--open { border-color: var(--accent); }
.sp-trigger__name { font-size: 13px; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; min-width: 0; }
.sp-trigger__meta { display: flex; align-items: center; gap: 5px; flex: none; }
.sp-menu {
  position: absolute; top: calc(100% + 6px); left: 0; z-index: 400;
  background: var(--bg-base); border: 1px solid var(--line-strong);
  border-radius: 12px; box-shadow: 0 12px 32px rgba(0,0,0,.4); width: 360px; overflow: hidden;
}
.sp-search { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--line); }
.sp-search__input { flex: 1; background: none; border: none; outline: none; font-family: inherit; font-size: 13px; color: var(--text); }
.sp-search__input::placeholder { color: var(--text-faint); }
.sp-filters { display: flex; gap: 6px; padding: 8px 10px; flex-wrap: wrap; border-bottom: 1px solid var(--line); background: var(--bg-sunken); }
.sp-divider { height: 1px; background: var(--line); }
.sp-list { max-height: 260px; overflow-y: auto; padding: 4px 0; }
.sp-empty { padding: 16px 14px; font-size: 12px; color: var(--text-muted); text-align: center; }
.sp-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; cursor: pointer; transition: background .1s; }
.sp-item:hover { background: var(--bg-raised); }
.sp-item--active { background: var(--accent-soft); }
.sp-item__check { width: 16px; flex: none; color: var(--accent); }
.sp-item__body { flex: 1; min-width: 0; }
.sp-item__title { font-size: 13px; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sp-item__meta { display: flex; gap: 4px; margin-top: 3px; }
.sp-item__count { font-size: 11px; color: var(--text-muted); flex: none; white-space: nowrap; }

.seg { display: flex; background: var(--bg-sunken); border-radius: 8px; padding: 3px; gap: 2px; }
.seg__btn { font-size: 11px; line-height: 1; padding: 4px 10px; border-radius: 5px; border: none; background: none; cursor: pointer; color: var(--text-secondary); font-family: inherit; white-space: nowrap; transition: color .12s; }
.seg__btn:hover { color: var(--text); }
.seg__btn--on { background: var(--bg-base); color: var(--text); box-shadow: 0 1px 3px rgba(0,0,0,.22); }

/* ── Версии ───────────────────────────────────────────────────────── */
.report-meta { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.ver-nav { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ver-btn {
  width: 24px; height: 24px; flex: none; display: grid; place-items: center;
  border: 1px solid var(--line-strong); border-radius: 7px;
  background: var(--bg-sunken); color: var(--text-secondary); cursor: pointer; transition: color .12s, border-color .12s;
}
.ver-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent-text); }
.ver-btn:disabled { opacity: .35; cursor: default; }
.ver-label { font-size: 12px; font-weight: 600; color: var(--text); }

/* ── KPI-сравнение ────────────────────────────────────────────────── */
.kpi-deltas { display: flex; gap: 10px; flex-wrap: wrap; }
.kpi-delta {
  flex: 1; min-width: 120px; padding: 10px 12px;
  background: var(--bg-sunken); border: 1px solid var(--line); border-radius: 10px;
}
.kpi-delta__label { font-size: 11px; color: var(--text-muted); }
.kpi-delta__val { font-size: 20px; font-weight: 700; color: var(--text); margin-top: 2px; font-variant-numeric: tabular-nums; }
.kpi-delta__suf { font-size: 12px; font-weight: 500; color: var(--text-muted); margin-left: 1px; }
.kpi-delta__chg { font-size: 11px; font-weight: 600; margin-top: 3px; font-variant-numeric: tabular-nums; }
.chg-up { color: var(--sev-low-text, #4ade80); }
.chg-down { color: var(--sev-crit-text); }
.chg-neutral { color: var(--text-secondary); }
.chg-flat { color: var(--text-faint); font-weight: 500; }

/* ── Отчёт ────────────────────────────────────────────────────────── */
.sec-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.sec-text { font-size: 13px; line-height: 1.6; color: var(--text-secondary); margin: 0; }
.sec-list { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 6px; }
.sec-list li { font-size: 13px; line-height: 1.5; color: var(--text-secondary); }

/* ── Генерация ────────────────────────────────────────────────────── */
.gen-state { display: flex; align-items: center; gap: 14px; padding: 18px; }
.gen-spinner {
  width: 44px; height: 44px; border-radius: 12px; flex: none;
  display: flex; align-items: center; justify-content: center;
  background: var(--accent-soft); color: var(--accent);
  animation: gen-pulse 1.2s ease-in-out infinite;
}
@keyframes gen-pulse { 0%,100% { opacity: .55; transform: scale(.96); } 50% { opacity: 1; transform: scale(1.04); } }
</style>
