<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import PhCard from '../components/ui/PhCard.vue'
import PhEmptyState from '../components/ui/PhEmptyState.vue'
import { api } from '../lib/api'

const CH_LABEL = { push: 'Web Push', telegram: 'Telegram', sms: 'SMS', email: 'E-mail' }

const surveys = ref([])
const surveyId = ref('')
const data = ref(null)
const loading = ref(false)

onMounted(async () => {
  const dash = await api('/surveys/dashboard/')
  surveys.value = (dash.surveys || []).filter(s => s.response_count > 0)
  if (dash.survey) surveyId.value = String(dash.survey.id)
  else if (surveys.value.length) surveyId.value = String(surveys.value[0].id)
})

watch(surveyId, async (id) => {
  if (!id) { data.value = null; return }
  loading.value = true
  try { data.value = await api(`/notifications/delivery/${id}`) }
  finally { loading.value = false }
})

const channels = computed(() => data.value?.channels || [])
const totalSent = computed(() => channels.value.reduce((a, c) => a + c.sent, 0))
const maxSent = computed(() => Math.max(1, ...channels.value.map(c => c.sent)))
const totalCost = computed(() => data.value?.total_cost ?? 0)

function fmtMin(m) {
  if (m == null) return '—'
  if (m < 60) return `${m} мин`
  const h = Math.floor(m / 60), r = m % 60
  return r ? `${h} ч ${r} мин` : `${h} ч`
}
</script>

<template>
  <div class="route" style="display:flex;flex-direction:column;gap:14px">
    <PhCard :pad="false">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 18px">
        <div>
          <div class="h3" style="font-size:15px">Эффективность каналов уведомлений</div>
          <div class="xs muted" style="margin-top:2px">
            Отправлено / открыто / CTR / стоимость SMS / скорость отклика — каскад Web Push → Telegram → SMS → E-mail
          </div>
        </div>
        <select class="select" v-model="surveyId" style="min-width:220px">
          <option v-for="s in surveys" :key="s.id" :value="String(s.id)">{{ s.title }}</option>
        </select>
      </div>
    </PhCard>

    <PhCard v-if="!surveyId || !channels.length">
      <PhEmptyState icon="bell" title="Нет данных по доставке"
        body="Опубликуйте опрос и дождитесь рассылки — метрики каналов появятся здесь." />
    </PhCard>

    <template v-else>
      <div class="kpi-row">
        <PhCard :pad="false"><div style="padding:14px 16px">
          <div class="kpi__label">Всего отправлено</div>
          <div class="kpi__val">{{ totalSent }}</div>
        </div></PhCard>
        <PhCard :pad="false"><div style="padding:14px 16px">
          <div class="kpi__label">Стоимость SMS за период</div>
          <div class="kpi__val">{{ totalCost.toFixed(2) }} <span class="unit">₽</span></div>
        </div></PhCard>
      </div>

      <PhCard :pad="false">
        <table class="ch-table">
          <thead>
            <tr>
              <th>Канал</th><th>Отправлено</th><th>Открыто</th><th>Переходы</th>
              <th>CTR</th><th>Ср. время до прохождения</th><th>Стоимость</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in channels" :key="c.channel">
              <td style="font-weight:600">{{ CH_LABEL[c.channel] || c.channel }}</td>
              <td>
                <div class="bar-wrap">
                  <div class="bar" :style="{ width: (c.sent / maxSent * 100) + '%' }" />
                  <span>{{ c.sent }}</span>
                </div>
              </td>
              <td>{{ c.opened }}</td>
              <td>{{ c.clicked }}</td>
              <td><span :class="['ctr', c.ctr >= 50 ? 'ctr--good' : '']">{{ c.ctr }}%</span></td>
              <td>{{ fmtMin(c.avg_to_action_min) }}</td>
              <td>{{ c.cost ? c.cost.toFixed(2) + ' ₽' : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </PhCard>
    </template>
  </div>
</template>

<style scoped>
.kpi-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.ch-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ch-table th {
  text-align: left; padding: 10px 14px; font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: .05em; color: var(--text-muted);
  border-bottom: 1px solid var(--line);
}
.ch-table td { padding: 11px 14px; border-bottom: 1px solid var(--line); color: var(--text); }
.ch-table tr:last-child td { border-bottom: none; }
.bar-wrap { display: flex; align-items: center; gap: 8px; }
.bar { height: 7px; border-radius: 4px; background: var(--accent); min-width: 2px; }
.bar-wrap span { font-variant-numeric: tabular-nums; }
.ctr { font-weight: 600; color: var(--text-muted); }
.ctr--good { color: #4ade80; }
</style>
