<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PhLogo from '../components/ui/PhLogo.vue'
import PhIcon from '../components/ui/PhIcon.vue'
import PhButton from '../components/ui/PhButton.vue'
import QuestionInput from '../components/QuestionInput.vue'
import { api } from '../lib/api'
import { useAuth } from '../stores/useAuth'

const route = useRoute()
const router = useRouter()
const auth = useAuth()

const survey = ref(null)
const banner = ref('')
const questions = ref([])
const answers = reactive({})
const orderToId = {}
const i = ref(0)
const done = ref(false)
const already = ref(false)
const error = ref('')
const intro = ref(true)   // показываем intro до нажатия «Начать»
const loading = ref(true)

onMounted(async () => {
  const data = await api(`/surveys/${route.params.id}/take/`)
  survey.value = data
  banner.value = data.banner
  questions.value = [...data.questions].sort((a, b) => a.order - b.order)
  questions.value.forEach((q) => { orderToId[q.order] = q.id })
  already.value = data.already_participated
  i.value = findVisible(0, 1)
  loading.value = false
  // если уже пройден — пропустить intro
  if (already.value) intro.value = false
  // переход по ссылке уведомления (?ch=push|telegram|sms|email) → метрика канала
  trackNotif('opened')
})

// Атрибуция доставки по каналам (ТЗ «Метрики доставки»): ссылка несёт ?ch=<канал>.
function trackNotif(event) {
  const channel = route.query.ch
  if (!channel) return
  api('/notifications/track', {
    method: 'POST', body: { survey_id: Number(route.params.id), channel, event },
  }).catch(() => { /* метрика не критична */ })
}

function startSurvey() { intro.value = false }

// --- движок ветвления (conditional logic) ---
function evalRule(rule) {
  const val = answers[orderToId[rule.question]]
  const t = rule.value
  switch (rule.op) {
    case 'eq': return String(val) === String(t)
    case 'ne': return String(val) !== String(t)
    case 'lte': return Number(val) <= Number(t)
    case 'gte': return Number(val) >= Number(t)
    case 'in': return Array.isArray(t) && t.includes(val)
    default: return true
  }
}
function isVisible(q) {
  const r = q.branch_rules && q.branch_rules.show_if
  if (!r) return true
  if (answers[orderToId[r.question]] == null) return false
  return evalRule(r)
}
function findVisible(start, dir) {
  let k = start
  while (k >= 0 && k < questions.value.length) {
    if (isVisible(questions.value[k])) return k
    k += dir
  }
  return dir > 0 ? questions.value.length : -1
}

const current = computed(() => questions.value[i.value])
const visibleList = computed(() => questions.value.filter(isVisible))
const progress = computed(() => {
  const total = visibleList.value.length || 1
  const passed = questions.value.slice(0, i.value + 1).filter(isVisible).length
  return Math.round((passed / total) * 100)
})
const stepNo = computed(() => questions.value.slice(0, i.value + 1).filter(isVisible).length)
const answeredCurrent = computed(() => {
  const q = current.value
  if (!q || !q.required) return true
  const v = answers[q.id]
  if (q.qtype === 'multi') return Array.isArray(v) && v.length > 0
  if (q.qtype === 'text') return !!(v && v.trim())
  if (q.qtype === 'matrix') return v && Object.keys(v).length > 0
  return v != null
})

function back() { const p = findVisible(i.value - 1, -1); if (p >= 0) i.value = p }
async function next() {
  const n = findVisible(i.value + 1, 1)
  if (n >= questions.value.length) return finish()
  i.value = n
}

function buildPayload() {
  const out = []
  for (const q of questions.value) {
    if (!isVisible(q)) continue
    const v = answers[q.id]
    if (v == null || v === '') continue
    if (q.qtype === 'scale') out.push({ question_id: q.id, value_num: v })
    else if (q.qtype === 'text') out.push({ question_id: q.id, value_text: v })
    else out.push({ question_id: q.id, value_json: v })
  }
  return out
}
async function finish() {
  error.value = ''
  try {
    await api(`/surveys/${route.params.id}/submit/`, { method: 'POST', body: { answers: buildPayload() } })
    trackNotif('clicked')  // целевое действие выполнено через канал
    done.value = true
  } catch (e) {
    if (e.status === 409) { already.value = true } else { error.value = 'Не удалось отправить ответы' }
  }
}
function exit() { router.push(auth.isHr ? '/' : '/me') }
</script>

<template>
  <div class="survey-screen route">
    <div class="survey-top">
      <PhLogo :mark-size="24" :mark-radius="7" :wordmark-size="15" :gap="9" />
      <span class="anon"><PhIcon name="lock" :size="13" />{{ survey?.mode === 'identified' ? 'Ответы видны HR' : 'Ответы анонимны' }}</span>
    </div>

    <div class="survey-body">

      <!-- загрузка -->
      <div v-if="loading" class="muted sm" style="text-align:center;padding:40px">Загрузка…</div>

      <!-- intro -->
      <div v-else-if="intro && !already" class="qcard route" style="max-width:520px">
        <button style="display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--text-secondary);background:none;border:none;cursor:pointer;padding:0;margin-bottom:20px" @click="exit">
          <PhIcon name="arrow" :size="14" style="transform:rotate(180deg)" />Все опросы
        </button>
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px">
          <span class="badge" :class="survey.mode === 'anonymous' ? 'badge--low' : 'badge--neutral'">
            <span class="badge__dot" />{{ survey.mode === 'anonymous' ? 'Анонимный' : 'Идентифицированный' }}
          </span>
          <span v-if="survey.critical" class="badge badge--crit"><span class="badge__dot" />Обязательный</span>
        </div>

        <h1 class="h1" style="margin-bottom:12px;font-size:22px">{{ survey.title }}</h1>

        <p v-if="survey.description" class="body secondary" style="margin-bottom:20px;line-height:1.6">{{ survey.description }}</p>

        <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:28px">
          <div class="info-chip"><PhIcon name="survey" :size="14" />{{ questions.length }} вопросов</div>
          <div class="info-chip"><PhIcon name="clock" :size="14" />~{{ questions.length }} мин</div>
          <div v-if="survey.ends_at" class="info-chip">
            <PhIcon name="clock" :size="14" />до {{ new Date(survey.ends_at).toLocaleDateString('ru', { day:'numeric', month:'long' }) }}
          </div>
        </div>

        <div class="anon" style="margin-bottom:28px">
          <PhIcon name="lock" :size="13" />
          {{ survey.mode === 'anonymous'
              ? 'Ваши ответы анонимны — мы не сохраняем имя или IP, только общую статистику.'
              : 'Идентифицированный режим — ответы видны HR с указанием вашего имени.' }}
        </div>

        <PhButton variant="primary" size="lg" icon-right="arrow" style="width:100%" @click="startSurvey">
          Начать опрос
        </PhButton>
      </div>

      <!-- уже пройден -->
      <div v-else-if="already" class="thanks route">
        <div class="thanks__check"><PhIcon name="check" :size="34" :stroke="2" /></div>
        <h1 class="h1" style="margin-bottom:10px">Опрос уже пройден</h1>
        <p class="body secondary" style="margin-bottom:26px">Повторное прохождение недоступно — спасибо!</p>
        <PhButton variant="primary" icon-right="arrow" @click="exit">Готово</PhButton>
      </div>

      <!-- спасибо -->
      <div v-else-if="done" class="thanks route">
        <div class="thanks__check"><PhIcon name="check" :size="34" :stroke="2" /></div>
        <h1 class="h1" style="margin-bottom:10px">Спасибо за ответы!</h1>
        <p class="body secondary" style="margin-bottom:26px">
          {{ survey?.mode === 'identified'
            ? 'Ваши ответы переданы HR с указанием имени.'
            : 'Ваш голос учтён анонимно — в общей статистике отдела.' }}
        </p>
        <PhButton variant="primary" icon-right="arrow" @click="exit">Готово</PhButton>
      </div>

      <!-- вопрос -->
      <div v-else-if="current" class="qcard q-anim" :key="current.id">
        <div class="qprogress">
          <span class="qcount">{{ String(stepNo).padStart(2, '0') }} / {{ String(visibleList.length).padStart(2, '0') }}</span>
          <div class="qbar"><i :style="{ width: progress + '%' }" /></div>
        </div>

        <div v-if="banner" class="anon" style="margin-bottom:20px"><PhIcon name="lock" :size="13" />{{ banner }}</div>
        <h2 class="qtext">{{ current.text }}</h2>
        <p v-if="!current.required" class="qhint">Необязательный вопрос</p>

        <QuestionInput :question="current" :model-value="answers[current.id] ?? null"
          @update:model-value="answers[current.id] = $event" />

        <p v-if="error" class="xs" style="color:var(--sev-crit-text);margin-top:16px">{{ error }}</p>

        <div style="display:flex;gap:10px;justify-content:center;margin-top:36px">
          <PhButton v-if="stepNo > 1" variant="ghost" icon="arrow" style="flex-direction:row-reverse" @click="back">Назад</PhButton>
          <PhButton variant="primary" size="lg" icon-right="arrow" :disabled="!answeredCurrent"
            :style="{ opacity: answeredCurrent ? 1 : 0.5, minWidth: '150px' }" @click="next">
            {{ findVisible(i + 1, 1) >= questions.length ? 'Завершить' : 'Далее' }}
          </PhButton>
        </div>
      </div>

    </div>

    <div style="text-align:center;padding:0 26px 18px;flex:none">
      <p class="xs" style="color:var(--text-faint);display:inline-flex;gap:7px;align-items:center">
        <PhIcon name="lock" :size="12" />
        {{ survey?.mode === 'identified'
          ? 'Идентифицированный опрос — ответы привязаны к вашему аккаунту.'
          : 'Мы не сохраняем имя, e-mail или IP. Только ответы — в общей статистике отдела.' }}
      </p>
    </div>
  </div>
</template>
