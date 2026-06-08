<script setup>
import { ref, computed, onMounted } from 'vue'
import PhCard from '../components/ui/PhCard.vue'
import PhEmptyState from '../components/ui/PhEmptyState.vue'
import { api } from '../lib/api'

const surveys = ref([])
onMounted(async () => { surveys.value = await api('/surveys/') })
const past = computed(() => surveys.value.filter((s) => ['completed', 'archive'].includes(s.status)))
</script>

<template>
  <PhCard v-if="past.length === 0"><PhEmptyState icon="clock" title="История пуста" body="Завершённые и архивные опросы появятся здесь." /></PhCard>
  <PhCard v-else :pad="false" class="route">
    <table class="tbl">
      <thead><tr><th>Опрос</th><th>Режим</th><th>Ответов</th><th style="text-align:right">Статус</th></tr></thead>
      <tbody>
        <tr v-for="s in past" :key="s.id">
          <td style="font-weight:600">{{ s.title }}</td>
          <td class="muted">{{ s.mode === 'anonymous' ? 'анонимный' : 'идентиф.' }}</td>
          <td class="tnum">{{ s.response_count }}</td>
          <td style="text-align:right"><span class="badge badge--neutral">{{ s.status === 'completed' ? 'завершён' : 'архив' }}</span></td>
        </tr>
      </tbody>
    </table>
  </PhCard>
</template>
