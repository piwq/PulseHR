<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import PhCard from '../components/ui/PhCard.vue'
import PhSeverityBadge from '../components/ui/PhSeverityBadge.vue'
import PhEmptyState from '../components/ui/PhEmptyState.vue'
import PhModal from '../components/ui/PhModal.vue'
import PhButton from '../components/ui/PhButton.vue'
import PhIcon from '../components/ui/PhIcon.vue'
import { api } from '../lib/api'
import { sevLabel } from '../lib/severity'
import { useAppAction } from '../stores/useAppAction'
import { useToasts } from '../stores/useToasts'

const data    = ref(null)
const surveys = ref([])
onMounted(async () => {
  data.value = await api('/surveys/dashboard/')
  try { surveys.value = await api('/surveys/') } catch {}
})

const alerts = computed(() =>
  (data.value?.departments || []).filter(d => !d.suppressed && d.sev !== 'low'),
)

// ── Данные ────────────────────────────────────────────────────────
const activeSurveys = computed(() => surveys.value.filter(s => s.status === 'active'))
const allDepts = computed(() =>
  (data.value?.departments || []).filter(d => !d.suppressed).map(d => d.department),
)

// ── Состояние ─────────────────────────────────────────────────────
const modalOpen    = ref(false)
const confirmOpen  = ref(false)
const sending      = ref(false)
const surveyMenuOpen = ref(false)
const deptMenuOpen   = ref(false)

const selSurveyIds = ref([])   // number[]
const selDepts     = ref([])   // string[]  — пусто = все

function closePickers() { surveyMenuOpen.value = false; deptMenuOpen.value = false }

// ── Хелперы выбора опросов ────────────────────────────────────────
const allSurveysChecked = computed(() =>
  activeSurveys.value.length > 0 &&
  activeSurveys.value.every(s => selSurveyIds.value.includes(s.id)),
)
const someSurveysChecked = computed(() =>
  selSurveyIds.value.length > 0 && !allSurveysChecked.value,
)
function toggleAllSurveys() {
  selSurveyIds.value = allSurveysChecked.value ? [] : activeSurveys.value.map(s => s.id)
}
function toggleSurvey(id) {
  const i = selSurveyIds.value.indexOf(id)
  i >= 0 ? selSurveyIds.value.splice(i, 1) : selSurveyIds.value.push(id)
}

// ── Хелперы выбора отделов ────────────────────────────────────────
// пустой selDepts = «все отделы»
const allDeptsSelected = computed(() => selDepts.value.length === 0)
const someDeptsSelected = computed(() => selDepts.value.length > 0 && selDepts.value.length < allDepts.value.length)

function toggleAllDepts() {
  selDepts.value = allDeptsSelected.value ? [...allDepts.value] : []
}
function toggleDept(d) {
  const i = selDepts.value.indexOf(d)
  i >= 0 ? selDepts.value.splice(i, 1) : selDepts.value.push(d)
  // если выбраны все — сбросить в «все» (пустой массив = все)
  if (selDepts.value.length === allDepts.value.length) selDepts.value = []
}
function isDeptChecked(d) {
  return allDeptsSelected.value || selDepts.value.includes(d)
}

const deptLabel = computed(() => {
  if (allDeptsSelected.value) return 'Все отделы'
  if (selDepts.value.length === 1) return selDepts.value[0]
  return selDepts.value.length + ' отд.'
})
const surveyLabel = computed(() => {
  if (selSurveyIds.value.length === 0) return 'Выберите опросы'
  if (selSurveyIds.value.length === activeSurveys.value.length) return 'Все опросы'
  if (selSurveyIds.value.length === 1) {
    return activeSurveys.value.find(s => s.id === selSurveyIds.value[0])?.title ?? '1 опрос'
  }
  return selSurveyIds.value.length + ' опроса(ов)'
})

const toasts    = useToasts()
const appAction = useAppAction()
watch(() => appAction.trigger, () => {
  selSurveyIds.value = []
  selDepts.value     = []
  confirmOpen.value  = false
  closePickers()
  modalOpen.value    = true
})

const canProceed = computed(() => selSurveyIds.value.length > 0)

// ── План подтверждения ────────────────────────────────────────────
const targetDepts = computed(() =>
  allDeptsSelected.value ? allDepts.value : selDepts.value,
)

const confirmPlan = computed(() =>
  activeSurveys.value
    .filter(s => selSurveyIds.value.includes(s.id))
    .map(survey => {
      const restricted = survey.audience_departments || []
      const target = targetDepts.value

      if (restricted.length === 0) {
        const isAll = allDeptsSelected.value
        return { survey, willSend: isAll ? [] : target, skipped: [], isAll }
      }
      const willSend = target.filter(d => restricted.includes(d))
      const skipped  = target.filter(d => !restricted.includes(d))
      return { survey, willSend, skipped, isAll: false }
    }),
)

// ── Отправка ──────────────────────────────────────────────────────
async function executeAlert() {
  sending.value = true
  let totalQueued = 0
  try {
    for (const item of confirmPlan.value) {
      if (item.isAll) {
        const res = await api('/notifications/send-alert', {
          method: 'POST', body: { survey_id: item.survey.id, department: '' },
        })
        totalQueued += res.queued ?? 0
      } else {
        for (const dept of item.willSend) {
          const res = await api('/notifications/send-alert', {
            method: 'POST', body: { survey_id: item.survey.id, department: dept },
          })
          totalQueued += res.queued ?? 0
        }
      }
    }
    toasts.push({
      tone: 'medium', badge: 'info',
      title: 'Уведомления поставлены в очередь',
      body: `${confirmPlan.value.length} опрос(ов) · ${totalQueued} новых заданий`,
    })
    confirmOpen.value = false
    modalOpen.value   = false
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="route" style="display:flex;flex-direction:column;gap:12px" @click="closePickers">
    <PhCard v-if="alerts.length === 0">
      <PhEmptyState icon="check" title="Сигналов нет" body="Все отделы в пределах нормы." />
    </PhCard>
    <PhCard v-for="d in alerts" :key="d.department" hover>
      <div style="display:flex;gap:16px;align-items:flex-start">
        <div style="margin-top:2px"><PhSeverityBadge :level="d.sev" pulse>{{ sevLabel(d.sev) }}</PhSeverityBadge></div>
        <div style="flex:1;min-width:0">
          <div class="h3" style="font-size:15px">
            Отдел «{{ d.department }}»: {{ d.sev === 'critical' ? 'критический сигнал' : 'требует внимания' }}
          </div>
          <p class="sm muted" style="margin-top:4px">
            {{ d.note }}. Вовлечённость {{ d.eng?.toFixed(1) }} / 5{{ d.enps != null ? `, eNPS ${d.enps > 0 ? '+' : ''}${d.enps}` : '' }}.
          </p>
        </div>
      </div>
    </PhCard>
  </div>

  <!-- ── Шаг 1 ── -->
  <PhModal :open="modalOpen" title="Разослать алерт" @close="modalOpen = false" :width="480">
    <div style="display:flex;flex-direction:column;gap:16px" @click.stop="closePickers">
      <p class="sm muted">Сотрудники получат напоминание по каскаду: Web Push → Telegram → SMS → E-mail.</p>

      <!-- Пикер опросов -->
      <div>
        <div class="picker-label">Опросы</div>
        <div style="position:relative" @click.stop>
          <button class="dept-btn" :class="selSurveyIds.length && 'dept-btn--active'"
            @click="surveyMenuOpen = !surveyMenuOpen; deptMenuOpen = false">
            {{ surveyLabel }}
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 3.5l3 3 3-3"/></svg>
          </button>
          <div v-if="surveyMenuOpen" class="dept-menu">
            <div class="dept-toggle-all" @click="toggleAllSurveys">
              <input type="checkbox" :checked="allSurveysChecked" :indeterminate="someSurveysChecked" readonly />
              <span>{{ allSurveysChecked ? 'Снять все' : 'Выбрать все' }}</span>
            </div>
            <div class="dept-sep" />
            <label v-for="s in activeSurveys" :key="s.id" class="dept-item">
              <input type="checkbox" :checked="selSurveyIds.includes(s.id)" @change="toggleSurvey(s.id)" />
              <span style="flex:1;min-width:0">{{ s.title }}</span>
              <span class="xs muted" style="flex:none">{{ s.response_count }} отв.</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Пикер отделов -->
      <div>
        <div class="picker-label">Отделы</div>
        <div style="position:relative" @click.stop>
          <button class="dept-btn" :class="!allDeptsSelected && 'dept-btn--active'"
            @click="deptMenuOpen = !deptMenuOpen; surveyMenuOpen = false">
            {{ deptLabel }}
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 3.5l3 3 3-3"/></svg>
          </button>
          <div v-if="deptMenuOpen" class="dept-menu">
            <div class="dept-toggle-all" @click="toggleAllDepts">
              <input type="checkbox" :checked="allDeptsSelected" :indeterminate="someDeptsSelected" readonly />
              <span>{{ allDeptsSelected ? 'Все отделы' : 'Снять выбор' }}</span>
            </div>
            <div class="dept-sep" />
            <label v-for="d in allDepts" :key="d" class="dept-item">
              <input type="checkbox" :checked="isDeptChecked(d)" @change="toggleDept(d)" />
              <span>{{ d }}</span>
            </label>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
        <span class="xs muted">
          {{ selSurveyIds.length ? selSurveyIds.length + ' опрос(ов) · ' + (allDeptsSelected ? 'все отделы' : deptLabel) : 'Выберите опросы' }}
        </span>
        <div style="display:flex;gap:8px">
          <PhButton variant="ghost" @click="modalOpen = false">Отмена</PhButton>
          <PhButton variant="primary" :disabled="!canProceed" @click="confirmOpen = true; closePickers()">
            Далее <PhIcon name="arrow" :size="13" style="margin-left:2px" />
          </PhButton>
        </div>
      </div>
    </template>
  </PhModal>

  <!-- ── Шаг 2: Подтверждение ── -->
  <PhModal :open="confirmOpen" title="Подтверждение рассылки" @close="confirmOpen = false" :width="500">
    <div style="display:flex;flex-direction:column;gap:10px;overflow-y:auto;max-height:60vh">
      <p class="sm muted">Проверьте план рассылки перед отправкой.</p>
      <div v-for="item in confirmPlan" :key="item.survey.id" class="plan-item">
        <div class="plan-item__title">
          <PhIcon name="survey" :size="14" style="flex:none;color:var(--accent)" />
          «{{ item.survey.title }}»
        </div>
        <div v-if="item.isAll" class="plan-row plan-row--ok">
          <PhIcon name="check" :size="13" />Уведомления будут отправлены во все отделы
        </div>
        <template v-else-if="!item.skipped.length">
          <div class="plan-row plan-row--ok">
            <PhIcon name="check" :size="13" />Будут отправлены в: <strong>{{ item.willSend.join(', ') }}</strong>
          </div>
        </template>
        <template v-else>
          <div v-if="item.willSend.length" class="plan-row plan-row--ok">
            <PhIcon name="check" :size="13" />Будут отправлены в: <strong>{{ item.willSend.join(', ') }}</strong>
          </div>
          <div v-else class="plan-row plan-row--warn">
            <PhIcon name="alert" :size="13" />Ни один из выбранных отделов не входит в аудиторию опроса
          </div>
          <div class="plan-row plan-row--skip">
            <PhIcon name="x" :size="13" style="flex:none;margin-top:1px" />
            <span>Не будут отправлены: <strong>{{ item.skipped.join(', ') }}</strong> — не входят в аудиторию этого опроса</span>
          </div>
        </template>
      </div>
    </div>
    <template #footer>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <PhButton variant="ghost" @click="confirmOpen = false">← Назад</PhButton>
        <PhButton variant="primary"
          :disabled="sending || confirmPlan.every(i => !i.isAll && !i.willSend.length)"
          @click="executeAlert">
          {{ sending ? 'Отправка…' : 'Подтвердить и разослать' }}
        </PhButton>
      </div>
    </template>
  </PhModal>
</template>

<style scoped>
.picker-label {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: .06em; color: var(--text-muted); margin-bottom: 6px;
}

/* переиспользуем паттерн dept-btn/dept-menu из DashboardView */
.dept-btn {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid var(--line); border-radius: 8px; background: var(--bg-raised);
  font-size: 13px; font-family: inherit; color: var(--text-secondary);
  padding: 6px 12px; cursor: pointer; white-space: nowrap;
  transition: color .12s, border-color .12s;
}
.dept-btn:hover { border-color: var(--text-faint); color: var(--text); }
.dept-btn--active { color: var(--accent-text, var(--accent)); border-color: var(--accent); background: var(--accent-soft, color-mix(in srgb, var(--accent) 12%, transparent)); }

.dept-menu {
  position: absolute; top: calc(100% + 5px); left: 0; z-index: 400;
  background: var(--bg-base); border: 1px solid var(--line-strong, var(--line));
  border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,.35);
  min-width: 220px; max-height: 260px; overflow-y: auto; padding: 6px 0;
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
  font-weight: 600; color: var(--text-secondary); transition: background .1s;
}
.dept-toggle-all:hover { background: var(--bg-raised); }
.dept-toggle-all input[type=checkbox] { accent-color: var(--accent); width: 13px; height: 13px; flex: none; pointer-events: none; }
.dept-sep { height: 1px; background: var(--line); margin: 2px 0; }

/* план подтверждения */
.plan-item { border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
.plan-item__title {
  display: flex; align-items: center; gap: 7px;
  padding: 9px 12px; font-size: 13px; font-weight: 600;
  background: var(--bg-raised); border-bottom: 1px solid var(--line);
}
.plan-row {
  display: flex; align-items: flex-start; gap: 7px;
  padding: 7px 12px; font-size: 12px; border-bottom: 1px solid var(--line);
}
.plan-row:last-child { border-bottom: none; }
.plan-row--ok   { color: #4ade80; }
.plan-row--warn { color: var(--sev-crit-text); }
.plan-row--skip { color: var(--text-muted); }
.plan-row--ok strong, .plan-row--skip strong { color: var(--text); }
</style>
