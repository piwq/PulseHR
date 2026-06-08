<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import PhCard from '../components/ui/PhCard.vue'
import PhSeverityBadge from '../components/ui/PhSeverityBadge.vue'
import PhEmptyState from '../components/ui/PhEmptyState.vue'
import PhModal from '../components/ui/PhModal.vue'
import PhButton from '../components/ui/PhButton.vue'
import { api } from '../lib/api'
import { sevLabel } from '../lib/severity'
import { useAppAction } from '../stores/useAppAction'
import { useToasts } from '../stores/useToasts'

const data = ref(null)
const surveys = ref([])
onMounted(async () => {
  data.value = await api('/surveys/dashboard/')
  try { surveys.value = await api('/surveys/') } catch { /* ignore */ }
})
const alerts = computed(() => (data.value?.departments || []).filter((d) => !d.suppressed && d.sev !== 'low'))

// Модалка «Разослать алерт»
const modalOpen = ref(false)
const selSurveyId = ref('')
const selDept = ref('')
const sending = ref(false)
const result = ref(null)

const toasts = useToasts()
const appAction = useAppAction()
watch(() => appAction.trigger, () => {
  modalOpen.value = true
  selSurveyId.value = data.value?.survey?.id ? String(data.value.survey.id) : ''
  selDept.value = ''
  result.value = null
})

const depts = computed(() =>
  (data.value?.departments || []).filter((d) => !d.suppressed).map((d) => d.department),
)

async function sendAlert() {
  if (!selSurveyId.value) return
  sending.value = true
  result.value = null
  try {
    const res = await api('/notifications/send-alert', {
      method: 'POST',
      body: { survey_id: Number(selSurveyId.value), department: selDept.value },
    })
    result.value = res
    const target = selDept.value || 'все отделы'
    toasts.push({
      tone: 'medium',
      badge: 'info',
      title: `Уведомления поставлены в очередь`,
      body: `«${res.survey_title}» → ${target}: ${res.queued} новых заданий`,
    })
    modalOpen.value = false
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="route" style="display:flex;flex-direction:column;gap:12px">
    <PhCard v-if="alerts.length === 0"><PhEmptyState icon="check" title="Сигналов нет" body="Все отделы в пределах нормы." /></PhCard>
    <PhCard v-for="d in alerts" :key="d.department" hover>
      <div style="display:flex;gap:16px;align-items:flex-start">
        <div style="margin-top:2px"><PhSeverityBadge :level="d.sev" pulse>{{ sevLabel(d.sev) }}</PhSeverityBadge></div>
        <div style="flex:1;min-width:0">
          <div class="h3" style="font-size:15px">Отдел «{{ d.department }}»: {{ d.sev === 'critical' ? 'критический сигнал' : 'требует внимания' }}</div>
          <p class="sm muted" style="margin-top:4px">{{ d.note }}. Вовлечённость {{ d.eng?.toFixed(1) }} / 5{{ d.enps != null ? `, eNPS ${d.enps > 0 ? '+' : ''}${d.enps}` : '' }}.</p>
        </div>
      </div>
    </PhCard>
  </div>

  <PhModal :open="modalOpen" title="Разослать алерт" @close="modalOpen = false" :width="480">
    <div style="display:flex;flex-direction:column;gap:12px">
      <p class="sm muted">Сотрудники получат напоминание пройти опрос по каскаду: Web Push → Telegram → SMS → E-mail.</p>
      <div>
        <div class="xs muted" style="margin-bottom:5px">Опрос</div>
        <select class="select" v-model="selSurveyId" style="width:100%;font-size:13px">
          <option value="">— выберите опрос —</option>
          <option v-for="s in surveys" :key="s.id" :value="String(s.id)">
            {{ s.title }} ({{ s.response_count }} отв.)
          </option>
        </select>
      </div>
      <div>
        <div class="xs muted" style="margin-bottom:5px">Отдел (не обязательно)</div>
        <select class="select" v-model="selDept" style="width:100%;font-size:13px">
          <option value="">Все отделы</option>
          <option v-for="d in depts" :key="d" :value="d">{{ d }}</option>
        </select>
      </div>
    </div>
    <template #footer>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <PhButton variant="ghost" @click="modalOpen = false">Отмена</PhButton>
        <PhButton variant="primary" :disabled="!selSurveyId || sending" @click="sendAlert">
          {{ sending ? 'Отправка…' : 'Разослать' }}
        </PhButton>
      </div>
    </template>
  </PhModal>
</template>
