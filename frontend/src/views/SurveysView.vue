<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PhCard from '../components/ui/PhCard.vue'
import PhButton from '../components/ui/PhButton.vue'
import PhIcon from '../components/ui/PhIcon.vue'
import PhEmptyState from '../components/ui/PhEmptyState.vue'
import { api, getToken } from '../lib/api'

const router = useRouter()
const surveys = ref([])
const loading = ref(true)
const openMenu = ref(null)
const archiveOpen = ref(false)

// ── Сортировка ────────────────────────────────────────────────────────
const SORT_OPTS = [
  { key: 'date',      label: 'Дата создания',   dir: 'desc' },
  { key: 'title',     label: 'Название',         dir: 'asc'  },
  { key: 'questions', label: 'Вопросов',         dir: 'desc' },
  { key: 'responses', label: 'Ответов',          dir: 'desc' },
]
const sortKey = ref('date')
const sortDir = ref('desc')

function setSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = SORT_OPTS.find(o => o.key === key).dir
  }
}

function sortedList(list) {
  return [...list].sort((a, b) => {
    let va, vb
    if (sortKey.value === 'date')      { va = a.id;              vb = b.id }
    if (sortKey.value === 'title')     { va = a.title.toLowerCase(); vb = b.title.toLowerCase() }
    if (sortKey.value === 'questions') { va = a.questions.length; vb = b.questions.length }
    if (sortKey.value === 'responses') { va = a.response_count;  vb = b.response_count }
    if (va < vb) return sortDir.value === 'asc' ? -1 : 1
    if (va > vb) return sortDir.value === 'asc' ? 1 : -1
    return 0
  })
}

const activeSurveys   = computed(() => sortedList(surveys.value.filter(s => s.status === 'active')))
const archivedSurveys = computed(() => sortedList(surveys.value.filter(s => s.status !== 'active')))

const STATUS = {
  draft:     ['badge--neutral', 'черновик'],
  active:    ['badge--low',     'активен'],
  completed: ['badge--neutral', 'завершён'],
  archive:   ['badge--neutral', 'архив'],
}

onMounted(load)
async function load() {
  loading.value = true
  try { surveys.value = await api('/surveys/') } finally { loading.value = false }
}

function toggleMenu(id, e) { e.stopPropagation(); openMenu.value = openMenu.value === id ? null : id }
function closeMenu() { openMenu.value = null }

async function publish(s)  { await api(`/surveys/${s.id}/publish/`,  { method: 'POST' }); closeMenu(); load() }
async function complete(s) { await api(`/surveys/${s.id}/complete/`,  { method: 'POST' }); closeMenu(); load() }
async function archive(s)  { await api(`/surveys/${s.id}/archive/`,   { method: 'POST' }); closeMenu(); load() }
async function relaunch(s) {
  if (!confirm(`Перезапустить «${s.title}» новой волной?\nИстория прошлых волн сохранится для сравнения.`)) return
  await api(`/surveys/${s.id}/relaunch/`, { method: 'POST' }); closeMenu(); load()
}
function runsLabel(s) {
  const parts = [`${s.questions.length} вопросов`]
  if (s.run_count) parts.push(`${s.run_count} ${s.run_count === 1 ? 'волна' : 'волн'}`)
  parts.push(`${s.response_count} ответов`)
  return parts.join(' · ')
}
async function remove(s) {
  if (!confirm(`Удалить опрос «${s.title}»?\nЕго можно восстановить в течение 30 дней.`)) return
  await api(`/surveys/${s.id}/`, { method: 'DELETE' })
  closeMenu(); load()
}
function exportCsv(s) {
  fetch(`/api/surveys/${s.id}/export?fmt=xlsx`, { headers: { Authorization: 'Token ' + getToken() } })
    .then(r => r.blob()).then(b => {
      const url = URL.createObjectURL(b)
      const a = document.createElement('a'); a.href = url; a.download = `survey_${s.id}.xlsx`; a.click()
      URL.revokeObjectURL(url)
    })
  closeMenu()
}
</script>

<template>
  <div class="route" style="display:flex;flex-direction:column;gap:12px" @click="closeMenu">

    <PhCard v-if="loading"><div class="sm muted">Загрузка…</div></PhCard>

    <template v-else>
      <!-- Панель сортировки -->
      <div class="sort-bar">
        <span class="sort-bar__label">Сортировка:</span>
        <button v-for="opt in SORT_OPTS" :key="opt.key"
          class="sort-chip" :class="{ active: sortKey === opt.key }"
          @click.stop="setSort(opt.key)">
          {{ opt.label }}
          <span v-if="sortKey === opt.key" class="sort-chip__dir">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
        </button>
        <button v-if="sortKey !== 'date' || sortDir !== 'desc'" class="sort-chip sort-chip--reset"
          @click.stop="sortKey = 'date'; sortDir = 'desc'">✕ Сбросить</button>
      </div>

      <!-- Активные опросы -->
      <PhCard v-if="activeSurveys.length === 0">
        <PhEmptyState icon="survey" title="Нет активных опросов"
          :body="archivedSurveys.length ? 'Черновики и архив — в списке ниже.' : 'Создайте первый опрос в конструкторе.'" />
      </PhCard>

      <div v-for="s in activeSurveys" :key="s.id"
        :style="openMenu === s.id ? 'position:relative;z-index:200' : 'position:relative'">
        <PhCard hover>
          <div style="display:flex;align-items:center;gap:16px">
            <div style="flex:1;min-width:0;cursor:pointer" @click="router.push(`/surveys/${s.id}/edit`)">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <div class="h3" style="font-size:15px">{{ s.title }}</div>
                <span class="badge" :class="STATUS[s.status][0]"><span class="badge__dot" />{{ STATUS[s.status][1] }}</span>
                <span class="badge badge--neutral">{{ s.mode === 'anonymous' ? 'анонимный' : 'идентиф.' }}</span>
              </div>
              <p class="sm muted" style="margin-top:4px">{{ runsLabel(s) }}</p>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              <PhButton v-if="s.status === 'draft'" variant="primary" @click.stop="publish(s)">Опубликовать</PhButton>
              <div style="position:relative" @click.stop>
                <button class="iconbtn" :class="{ active: openMenu === s.id }"
                  style="width:34px;height:34px" title="Действия" @click="toggleMenu(s.id, $event)">
                  <PhIcon name="dots" :size="16" :stroke="2.5" />
                </button>
                <div v-if="openMenu === s.id" class="dropdown" style="right:0;left:auto;min-width:200px;top:calc(100% + 6px)">
                  <div class="dropdown__item" @click="router.push(`/surveys/${s.id}/edit`); closeMenu()"><PhIcon name="survey" :size="14" />Редактировать</div>
                  <div class="dropdown__item" @click="exportCsv(s)"><PhIcon name="trend" :size="14" />Экспорт XLSX</div>
                  <template v-if="s.status !== 'draft'">
                    <div class="dropdown__sep" />
                    <div v-if="s.status === 'active'" class="dropdown__item" @click="complete(s)"><PhIcon name="finish" :size="14" />Завершить досрочно</div>
                    <div v-if="s.status === 'completed' || s.status === 'archive'" class="dropdown__item" @click="relaunch(s)"><PhIcon name="refresh" :size="14" />Перезапустить (новая волна)</div>
                    <div v-if="s.status !== 'archive'" class="dropdown__item" @click="archive(s)"><PhIcon name="archive" :size="14" />Отправить в архив</div>
                  </template>
                  <div class="dropdown__sep" />
                  <div class="dropdown__item dropdown__item--danger" @click="remove(s)"><PhIcon name="x" :size="14" />Удалить</div>
                </div>
              </div>
            </div>
          </div>
        </PhCard>
      </div>

      <!-- Кнопка-раскрывашка -->
      <button v-if="archivedSurveys.length" class="archive-toggle" @click.stop="archiveOpen = !archiveOpen">
        <PhIcon name="archive" :size="14" />
        <span>Черновики, завершённые и архив · {{ archivedSurveys.length }}</span>
        <PhIcon name="arrow" :size="13" :style="{ transform: archiveOpen ? 'rotate(-90deg)' : 'rotate(90deg)', transition: 'transform .2s' }" />
      </button>

      <!-- Скрытые опросы -->
      <template v-if="archiveOpen">
        <div v-for="s in archivedSurveys" :key="s.id"
          :style="openMenu === s.id ? 'position:relative;z-index:200' : 'position:relative'">
          <PhCard hover>
            <div style="display:flex;align-items:center;gap:16px">
              <div style="flex:1;min-width:0;cursor:pointer" @click="router.push(`/surveys/${s.id}/edit`)">
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                  <div class="h3" style="font-size:15px">{{ s.title }}</div>
                  <span class="badge" :class="STATUS[s.status][0]"><span class="badge__dot" />{{ STATUS[s.status][1] }}</span>
                  <span class="badge badge--neutral">{{ s.mode === 'anonymous' ? 'анонимный' : 'идентиф.' }}</span>
                </div>
                <p class="sm muted" style="margin-top:4px">{{ runsLabel(s) }}</p>
              </div>
              <div style="display:flex;align-items:center;gap:8px">
                <PhButton v-if="s.status === 'draft'" variant="primary" @click.stop="publish(s)">Опубликовать</PhButton>
                <div style="position:relative" @click.stop>
                  <button class="iconbtn" :class="{ active: openMenu === s.id }"
                    style="width:34px;height:34px" title="Действия" @click="toggleMenu(s.id, $event)">
                    <PhIcon name="dots" :size="16" :stroke="2.5" />
                  </button>
                  <div v-if="openMenu === s.id" class="dropdown" style="right:0;left:auto;min-width:200px;top:calc(100% + 6px)">
                    <div class="dropdown__item" @click="router.push(`/surveys/${s.id}/edit`); closeMenu()"><PhIcon name="survey" :size="14" />Редактировать</div>
                    <div class="dropdown__item" @click="exportCsv(s)"><PhIcon name="trend" :size="14" />Экспорт XLSX</div>
                    <template v-if="s.status !== 'draft'">
                      <div class="dropdown__sep" />
                      <div v-if="s.status === 'active'" class="dropdown__item" @click="complete(s)"><PhIcon name="finish" :size="14" />Завершить досрочно</div>
                      <div v-if="s.status !== 'archive'" class="dropdown__item" @click="archive(s)"><PhIcon name="archive" :size="14" />Отправить в архив</div>
                      <div v-if="s.status === 'archive'" class="dropdown__item" @click="publish(s)"><PhIcon name="refresh" :size="14" />Восстановить</div>
                    </template>
                    <div class="dropdown__sep" />
                    <div class="dropdown__item dropdown__item--danger" @click="remove(s)"><PhIcon name="x" :size="14" />Удалить</div>
                  </div>
                </div>
              </div>
            </div>
          </PhCard>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.sort-bar {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
}
.sort-bar__label {
  font-size: 12px; color: var(--text-muted); margin-right: 2px;
}
.sort-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px; border-radius: 20px; border: 1px solid var(--line);
  background: var(--bg-raised); font-size: 12px; font-family: inherit;
  color: var(--text-muted); cursor: pointer; transition: background .12s, color .12s, border-color .12s;
}
.sort-chip:hover { color: var(--text); border-color: var(--text-muted); }
.sort-chip.active { background: var(--accent); border-color: var(--accent); color: #fff; }
.sort-chip--reset { color: var(--sev-crit-text); border-color: var(--sev-crit-text); }
.sort-chip--reset:hover { background: var(--sev-crit-text); color: #fff; }
.sort-chip__dir { font-size: 11px; opacity: .85; }

.archive-toggle {
  display: flex; align-items: center; gap: 8px; width: 100%;
  background: var(--bg-raised); border: 1px solid var(--line); border-radius: 12px;
  padding: 10px 14px; cursor: pointer; font-family: inherit; font-size: 13px;
  color: var(--text-muted); transition: background .12s, color .12s;
}
.archive-toggle:hover { background: var(--bg-hover, var(--line)); color: var(--text); }
.archive-toggle span { flex: 1; text-align: left; }
</style>
