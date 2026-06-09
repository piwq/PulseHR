<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PhCard from '../components/ui/PhCard.vue'
import PhButton from '../components/ui/PhButton.vue'
import PhField from '../components/ui/PhField.vue'
import PhInput from '../components/ui/PhInput.vue'
import PhIcon from '../components/ui/PhIcon.vue'
import OptionsEditor from '../components/OptionsEditor.vue'
import { api } from '../lib/api'

const route = useRoute()
const router = useRouter()
const editing = !!route.params.id

const TYPES = [['single', 'Одиночный выбор'], ['multi', 'Множественный выбор'],
  ['scale', 'Шкала (NPS/eNPS)'], ['text', 'Текст'], ['matrix', 'Матрица']]
const OPS = [['eq', '='], ['ne', '≠'], ['lte', '≤'], ['gte', '≥']]

const survey = ref({
  title: '', description: '', mode: 'anonymous', critical: false,
  starts_at: '', ends_at: '', questions: [],
})
const saving = ref(false)
const msg = ref('')
const runCount = ref(0)   // сколько волн уже было — после запуска вопросы менять нельзя

const allDepts = ref([])
const audienceDepts = ref([])
const audienceRoles = ref([])  // пусто = все роли (вся компания)
const ROLE_OPTS = [['employee', 'Сотрудники'], ['hr', 'HR / Руководители']]
const audienceSearch = ref('')
const audienceOpen = ref(false)

function toggleRole(r) {
  const i = audienceRoles.value.indexOf(r)
  if (i >= 0) audienceRoles.value.splice(i, 1)
  else audienceRoles.value.push(r)
}

const filteredDepts = computed(() =>
  allDepts.value.filter(d =>
    !audienceDepts.value.includes(d) &&
    d.toLowerCase().includes(audienceSearch.value.toLowerCase())
  )
)

function toggleDept(d) {
  const idx = audienceDepts.value.indexOf(d)
  if (idx >= 0) audienceDepts.value.splice(idx, 1)
  else { audienceDepts.value.push(d); audienceSearch.value = '' }
}
function removeDept(d) { audienceDepts.value = audienceDepts.value.filter(x => x !== d) }
function closeAudience() { setTimeout(() => { audienceOpen.value = false }, 150) }
function audienceKeydown(e) {
  if ((e.key === 'Enter' || e.key === ',') && audienceSearch.value.trim()) {
    e.preventDefault()
    const val = audienceSearch.value.trim()
    if (!audienceDepts.value.includes(val)) audienceDepts.value.push(val)
    audienceSearch.value = ''
  } else if (e.key === 'Backspace' && !audienceSearch.value && audienceDepts.value.length) {
    audienceDepts.value.pop()
  }
}

onMounted(async () => {
  allDepts.value = await api('/auth/departments').catch(() => [])
  if (!editing) { addQuestion(); return }
  const s = await api(`/surveys/${route.params.id}/`)
  runCount.value = s.run_count || 0
  audienceDepts.value = s.audience_departments || []
  audienceRoles.value = s.audience_roles || []
  survey.value = {
    title: s.title, description: s.description, mode: s.mode, critical: s.critical,
    starts_at: s.starts_at?.slice(0, 16) || '', ends_at: s.ends_at?.slice(0, 16) || '',
    questions: s.questions.map(fromApiQuestion),
  }
})

function newQuestion() {
  return {
    text: '', qtype: 'single', required: true,
    options: ['Вариант 1', 'Вариант 2'],
    min: 1, max: 5, low: '', high: '', nps: false,
    rows: ['Строка 1', 'Строка 2'], cols: ['Плохо', 'Нормально', 'Хорошо'],
    branch: { enabled: false, question: 1, op: 'eq', value: '' },
  }
}
function fromApiQuestion(q) {
  const c = q.config || {}
  const sif = q.branch_rules?.show_if
  return {
    text: q.text, qtype: q.qtype, required: q.required,
    options: c.options || ['Вариант 1', 'Вариант 2'],
    min: c.min ?? 1, max: c.max ?? 5, low: c.low || '', high: c.high || '', nps: !!c.nps,
    rows: c.rows || ['Строка 1'], cols: c.cols || ['Плохо', 'Хорошо'],
    branch: sif ? { enabled: true, ...sif } : { enabled: false, question: 1, op: 'eq', value: '' },
  }
}
function addQuestion() { survey.value.questions.push(newQuestion()) }
function removeQuestion(idx) { survey.value.questions.splice(idx, 1) }
function move(idx, dir) {
  const qs = survey.value.questions; const j = idx + dir
  if (j < 0 || j >= qs.length) return
  ;[qs[idx], qs[j]] = [qs[j], qs[idx]]
}
function clean(arr) { return arr.map((x) => x.trim()).filter(Boolean) }

function toApi() {
  return {
    title: survey.value.title,
    description: survey.value.description,
    mode: survey.value.mode,
    critical: survey.value.critical,
    audience_departments: audienceDepts.value,
    audience_roles: audienceRoles.value,
    starts_at: survey.value.starts_at || null,
    ends_at: survey.value.ends_at || null,
    questions: survey.value.questions.map((q, i) => {
      let config = {}
      if (q.qtype === 'single' || q.qtype === 'multi') config = { options: clean(q.options) }
      else if (q.qtype === 'scale') config = { min: Number(q.min), max: Number(q.max), low: q.low, high: q.high, nps: q.nps }
      else if (q.qtype === 'matrix') config = { rows: clean(q.rows), cols: clean(q.cols) }
      return {
        text: q.text, qtype: q.qtype, required: q.required, order: i + 1, config,
        branch_rules: q.branch.enabled
          ? { show_if: { question: Number(q.branch.question), op: q.branch.op, value: q.branch.value } }
          : {},
      }
    }),
  }
}

async function save(thenPublish = false) {
  saving.value = true
  msg.value = ''
  try {
    const body = toApi()
    const saved = editing
      ? await api(`/surveys/${route.params.id}/`, { method: 'PUT', body })
      : await api('/surveys/', { method: 'POST', body })
    if (thenPublish) await api(`/surveys/${saved.id}/publish/`, { method: 'POST' })
    router.push('/surveys')
  } catch (e) {
    msg.value = 'Ошибка сохранения: ' + (e.data ? JSON.stringify(e.data) : e.message)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="route" style="display:flex;flex-direction:column;gap:16px;max-width:760px" @click="audienceOpen = false">
    <div>
      <button style="display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--text-secondary);background:none;border:none;cursor:pointer;padding:0"
        @click="router.push('/surveys')">
        <PhIcon name="arrow" :size="14" style="transform:rotate(180deg)" />Все опросы
      </button>
    </div>
    <div v-if="runCount > 0" class="lock-note">
      <PhIcon name="alert" :size="15" style="flex:none;margin-top:1px" />
      <span>Опрос уже запускался ({{ runCount }} {{ runCount === 1 ? 'волна' : 'волн' }}).
        Изменение вопросов исказит сравнение с прошлыми волнами — меняйте их только осознанно.</span>
    </div>
    <PhCard>
      <div class="h3" style="margin-bottom:16px">Настройки опроса</div>
      <div style="display:flex;flex-direction:column;gap:14px">
        <PhField label="Название"><PhInput v-model="survey.title" placeholder="Пульс-опрос" /></PhField>
        <PhField label="Описание"><PhInput v-model="survey.description" placeholder="Короткое описание" /></PhField>
        <div style="display:flex;gap:14px;flex-wrap:wrap">
          <PhField label="Режим" style="flex:1;min-width:200px">
            <select class="select" v-model="survey.mode">
              <option value="anonymous">Анонимный</option>
              <option value="identified">Идентифицированный</option>
            </select>
          </PhField>
          <PhField label="Аудитория" style="flex:1;min-width:200px">
            <div style="position:relative">
              <div class="input" style="display:flex;flex-wrap:wrap;gap:4px;height:auto;min-height:38px;padding:5px 10px;cursor:text;align-items:center"
                @click.stop="audienceOpen = true">
                <span v-for="d in audienceDepts" :key="d"
                  style="display:inline-flex;align-items:center;gap:3px;background:var(--accent-soft);color:var(--accent-text);border-radius:4px;padding:2px 7px;font-size:12px;line-height:1.4">
                  {{ d }}
                  <button @mousedown.prevent="removeDept(d)"
                    style="background:none;border:none;cursor:pointer;color:inherit;padding:0;font-size:14px;line-height:1;opacity:.7">×</button>
                </span>
                <input v-model="audienceSearch"
                  @focus.stop="audienceOpen = true" @blur="closeAudience()"
                  @keydown="audienceKeydown"
                  :placeholder="audienceDepts.length ? '' : 'пусто = вся компания'"
                  style="border:none;background:none;outline:none;flex:1;min-width:80px;padding:0;color:var(--text);font-size:14px;font-family:inherit" />
              </div>
              <div v-if="audienceOpen && filteredDepts.length"
                class="dropdown" style="top:calc(100% + 4px);left:0;right:0;max-height:180px;overflow-y:auto"
                @click.stop>
                <div v-for="d in filteredDepts" :key="d" class="dropdown__item"
                  @mousedown.prevent="toggleDept(d)">{{ d }}</div>
              </div>
            </div>
          </PhField>
        </div>
        <PhField label="Роли в аудитории">
          <div style="display:flex;gap:18px;flex-wrap:wrap">
            <label v-for="[v, l] in ROLE_OPTS" :key="v"
              style="display:flex;align-items:center;gap:7px;font-size:13px;color:var(--text-secondary);cursor:pointer">
              <input type="checkbox" :checked="audienceRoles.includes(v)" @change="toggleRole(v)"
                style="accent-color:var(--accent);width:15px;height:15px" />{{ l }}
            </label>
            <span class="xs muted" style="align-self:center">пусто = все роли</span>
          </div>
        </PhField>
        <div style="display:flex;gap:14px;flex-wrap:wrap">
          <PhField label="Старт" style="flex:1"><input type="datetime-local" class="input" v-model="survey.starts_at" /></PhField>
          <PhField label="Окончание" style="flex:1"><input type="datetime-local" class="input" v-model="survey.ends_at" /></PhField>
        </div>
        <label style="display:flex;align-items:center;gap:10px;font-size:13px;color:var(--text-secondary)">
          <input type="checkbox" v-model="survey.critical" style="accent-color:var(--accent);width:15px;height:15px" />
          Критичный (доставка по каскаду независимо от настроек сотрудника)
        </label>
      </div>
    </PhCard>

    <PhCard v-for="(q, idx) in survey.questions" :key="idx" :pad="false">
      <div style="padding:18px 20px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
          <span class="mono xs" style="color:var(--text-muted)">Q{{ idx + 1 }}</span>
          <select class="select" v-model="q.qtype" style="width:auto">
            <option v-for="[v, l] in TYPES" :key="v" :value="v">{{ l }}</option>
          </select>
          <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-muted)">
            <input type="checkbox" v-model="q.required" style="accent-color:var(--accent)" />обяз.
          </label>
          <div style="margin-left:auto;display:flex;gap:4px">
            <button class="iconbtn" style="width:30px;height:30px" @click="move(idx, -1)"><PhIcon name="up" :size="14" /></button>
            <button class="iconbtn" style="width:30px;height:30px" @click="move(idx, 1)"><PhIcon name="down" :size="14" /></button>
            <button class="iconbtn" style="width:30px;height:30px" @click="removeQuestion(idx)"><PhIcon name="x" :size="14" /></button>
          </div>
        </div>

        <PhInput v-model="q.text" placeholder="Текст вопроса" style="margin-bottom:14px" />

        <!-- варианты для single / multi -->
        <div v-if="q.qtype === 'single' || q.qtype === 'multi'">
          <div class="label" style="margin-bottom:8px">Варианты ответа</div>
          <OptionsEditor v-model="q.options" placeholder="Текст варианта" />
        </div>

        <!-- шкала -->
        <div v-else-if="q.qtype === 'scale'" style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
          <PhField label="Мин" style="width:80px"><PhInput type="number" v-model="q.min" /></PhField>
          <PhField label="Макс" style="width:80px"><PhInput type="number" v-model="q.max" /></PhField>
          <PhField label="Подпись min" style="flex:1;min-width:120px"><PhInput v-model="q.low" /></PhField>
          <PhField label="Подпись max" style="flex:1;min-width:120px"><PhInput v-model="q.high" /></PhField>
          <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-muted);padding-bottom:10px">
            <input type="checkbox" v-model="q.nps" style="accent-color:var(--accent)" />eNPS
          </label>
        </div>

        <!-- матрица -->
        <div v-else-if="q.qtype === 'matrix'" style="display:flex;gap:24px;flex-wrap:wrap">
          <div style="flex:1;min-width:200px">
            <div class="label" style="margin-bottom:8px">Строки</div>
            <OptionsEditor v-model="q.rows" placeholder="Строка" add-label="Добавить строку" />
          </div>
          <div style="flex:1;min-width:200px">
            <div class="label" style="margin-bottom:8px">Колонки</div>
            <OptionsEditor v-model="q.cols" placeholder="Колонка" add-label="Добавить колонку" />
          </div>
        </div>

        <!-- ветвление -->
        <div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--line)">
          <label style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-secondary)">
            <input type="checkbox" v-model="q.branch.enabled" style="accent-color:var(--accent)" />
            Показывать по условию (ветвление)
          </label>
          <div v-if="q.branch.enabled" style="display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap">
            <span class="sm muted">Если ответ на</span>
            <select class="select" v-model="q.branch.question" style="width:auto">
              <option v-for="n in idx" :key="n" :value="n">Q{{ n }}</option>
            </select>
            <select class="select" v-model="q.branch.op" style="width:auto">
              <option v-for="[v, l] in OPS" :key="v" :value="v">{{ l }}</option>
            </select>
            <PhInput v-model="q.branch.value" placeholder="значение" style="width:160px" />
          </div>
        </div>
      </div>
    </PhCard>

    <PhButton variant="secondary" icon="grid" @click="addQuestion">Добавить вопрос</PhButton>

    <p v-if="msg" class="sm" style="color:var(--sev-crit-text)">{{ msg }}</p>
    <div style="display:flex;gap:10px">
      <PhButton variant="ghost" @click="save(false)" :disabled="saving">Сохранить черновик</PhButton>
      <PhButton variant="primary" icon-right="arrow" @click="save(true)" :disabled="saving">
        {{ saving ? 'Сохранение…' : 'Опубликовать' }}
      </PhButton>
    </div>
  </div>
</template>

<style scoped>
.lock-note {
  display: flex; align-items: flex-start; gap: 9px;
  padding: 11px 14px; border-radius: 10px; font-size: 13px; line-height: 1.45;
  color: var(--sev-warn-text, #fbbf24);
  background: color-mix(in srgb, var(--sev-warn-text, #fbbf24) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--sev-warn-text, #fbbf24) 30%, transparent);
}
</style>
