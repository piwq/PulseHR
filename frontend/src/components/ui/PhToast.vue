<script setup>
import PhIcon from './PhIcon.vue'
import PhSeverityBadge from './PhSeverityBadge.vue'
import { onMounted, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  tone: { type: String, default: 'critical' }, // critical | medium | low | accent
  title: { type: String, required: true },
  body: { type: String, default: undefined },
  badge: { type: String, default: undefined },
  time: { type: String, default: 'только что' },
  pulse: { type: Boolean, default: true },
  actions: { type: Array, default: () => [] }, // [{ id, label, variant }]
})
const emit = defineEmits(['close', 'action'])

const toneColor = {
  critical: 'var(--sev-crit)', medium: 'var(--sev-med)',
  low: 'var(--sev-low)', accent: 'var(--accent)',
}[props.tone]

const el = ref(null)
let timer = null
// belt-and-suspenders: snap to final visible state after the entrance duration,
// so a throttled/frozen animation clock can never leave the toast invisible.
onMounted(() => {
  timer = setTimeout(() => {
    if (el.value) {
      el.value.style.animation = 'none'
      el.value.style.opacity = '1'
      el.value.style.transform = 'none'
    }
  }, 360)
})
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <div class="toast enter" ref="el">
    <div class="toast__accent" :style="{ background: toneColor }" />
    <div style="flex:1;min-width:0">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
        <PhSeverityBadge v-if="badge" :level="tone" :pulse="pulse">{{ badge }}</PhSeverityBadge>
        <span class="xs muted">{{ time }}</span>
        <button @click="emit('close')"
          style="margin-left:auto;background:none;border:0;color:var(--text-faint);cursor:pointer;padding:2px;display:grid;place-items:center">
          <PhIcon name="x" :size="14" />
        </button>
      </div>
      <div class="sm" style="font-weight:700">{{ title }}</div>
      <div v-if="body" class="sm muted" style="margin-top:2px">{{ body }}</div>
      <div v-if="actions.length" style="margin-top:10px;display:flex;gap:8px">
        <button v-for="a in actions" :key="a.id" class="btn" :class="`btn--${a.variant || 'ghost'}`"
          style="padding:6px 12px;font-size:12.5px" @click="emit('action', a.id)">{{ a.label }}</button>
      </div>
    </div>
  </div>
</template>
