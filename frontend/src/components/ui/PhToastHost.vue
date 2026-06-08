<script setup>
import PhToast from './PhToast.vue'
import { useRouter } from 'vue-router'
import { useToasts } from '../../stores/useToasts'

const toasts = useToasts()
const router = useRouter()

// Known toast actions are kept as ids (not closures) so the store stays serialisable.
function onAction(toast, actionId) {
  if (actionId === 'open-dept') router.push('/alerts')
  toasts.remove(toast.id)
}
</script>

<template>
  <div style="position:fixed;top:16px;right:16px;z-index:60;display:flex;flex-direction:column;gap:10px">
    <PhToast v-for="t in toasts.items" :key="t.id"
      :tone="t.tone" :title="t.title" :body="t.body" :badge="t.badge"
      :time="t.time" :actions="t.actions || []"
      @close="toasts.remove(t.id)" @action="onAction(t, $event)" />
  </div>
</template>
