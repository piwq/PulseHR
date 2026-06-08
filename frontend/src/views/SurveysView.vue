<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PhCard from '../components/ui/PhCard.vue'
import PhButton from '../components/ui/PhButton.vue'
import PhIcon from '../components/ui/PhIcon.vue'
import PhEmptyState from '../components/ui/PhEmptyState.vue'
import { api, getToken } from '../lib/api'

const router = useRouter()
const surveys = ref([])
const loading = ref(true)
const openMenu = ref(null) // id открытого дропдауна

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
    <PhCard v-else-if="surveys.length === 0">
      <PhEmptyState icon="survey" title="Опросов пока нет" body="Создайте первый опрос в конструкторе." />
    </PhCard>

    <div v-for="s in surveys" :key="s.id" :style="openMenu === s.id ? 'position:relative;z-index:200' : 'position:relative'">
    <PhCard hover>
      <div style="display:flex;align-items:center;gap:16px">
        <div style="flex:1;min-width:0;cursor:pointer" @click="router.push(`/surveys/${s.id}/edit`)">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
            <div class="h3" style="font-size:15px">{{ s.title }}</div>
            <span class="badge" :class="STATUS[s.status][0]"><span class="badge__dot" />{{ STATUS[s.status][1] }}</span>
            <span class="badge badge--neutral">{{ s.mode === 'anonymous' ? 'анонимный' : 'идентиф.' }}</span>
          </div>
          <p class="sm muted" style="margin-top:4px">{{ s.questions.length }} вопросов · {{ s.response_count }} ответов</p>
        </div>

        <div style="display:flex;align-items:center;gap:8px">
          <!-- Опубликовать — заметная кнопка только для черновиков -->
          <PhButton v-if="s.status === 'draft'" variant="primary" @click.stop="publish(s)">Опубликовать</PhButton>

          <!-- Меню ⋯ -->
          <div style="position:relative" @click.stop>
            <button class="iconbtn" :class="{ active: openMenu === s.id }"
              style="width:34px;height:34px" title="Действия" @click="toggleMenu(s.id, $event)">
              <PhIcon name="dots" :size="16" :stroke="2.5" />
            </button>

            <div v-if="openMenu === s.id" class="dropdown" style="right:0;left:auto;min-width:200px;top:calc(100% + 6px)">
              <div class="dropdown__item" @click="router.push(`/surveys/${s.id}/edit`); closeMenu()">
                <PhIcon name="survey" :size="14" />Редактировать
              </div>
              <div class="dropdown__item" @click="exportCsv(s)">
                <PhIcon name="trend" :size="14" />Экспорт XLSX
              </div>

              <template v-if="s.status !== 'draft'">
                <div class="dropdown__sep" />
                <div v-if="s.status === 'active'" class="dropdown__item" @click="complete(s)">
                  <PhIcon name="finish" :size="14" />Завершить досрочно
                </div>
                <div v-if="s.status !== 'archive'" class="dropdown__item" @click="archive(s)">
                  <PhIcon name="archive" :size="14" />Отправить в архив
                </div>
                <div v-if="s.status === 'archive'" class="dropdown__item" @click="publish(s)">
                  <PhIcon name="refresh" :size="14" />Восстановить (активировать)
                </div>
              </template>

              <div class="dropdown__sep" />
              <div class="dropdown__item dropdown__item--danger" @click="remove(s)">
                <PhIcon name="x" :size="14" />Удалить
              </div>
            </div>
          </div>
        </div>
      </div>
    </PhCard>
    </div>
  </div>
</template>
