<script setup>
import { computed } from 'vue'

const SEV = {
  low: { cls: 'badge--low', label: 'норма' },
  medium: { cls: 'badge--med', label: 'внимание' },
  critical: { cls: 'badge--crit', label: 'критично' },
}

const props = defineProps({
  level: { type: String, default: 'low' }, // low | medium | critical
  pulse: { type: Boolean, default: false },
})

const meta = computed(() => SEV[props.level] || SEV.low)
const cls = computed(() => [
  'badge', meta.value.cls,
  props.level === 'critical' && props.pulse ? 'is-pulsing' : '',
].filter(Boolean).join(' '))
</script>

<template>
  <span :class="cls">
    <span class="badge__dot" /><slot>{{ meta.label }}</slot>
  </span>
</template>
