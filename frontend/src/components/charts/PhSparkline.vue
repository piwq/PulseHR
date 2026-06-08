<script setup>
import { computed } from 'vue'

const props = defineProps({
  values: { type: Array, required: true },
  color: { type: String, default: 'var(--accent)' },
  width: { type: Number, default: 96 },
  height: { type: Number, default: 30 },
})

const points = computed(() => {
  const min = Math.min(...props.values)
  const max = Math.max(...props.values)
  const pad = (max - min) * 0.15 || 1
  const lo = min - pad, hi = max + pad
  const stepX = props.width / (props.values.length - 1)
  const scaleY = (v) => {
    const t = (v - lo) / (hi - lo)
    return (props.height - 4) - t * ((props.height - 4) - 4)
  }
  return props.values.map((v, i) => `${i * stepX},${scaleY(v)}`).join(' ')
})
</script>

<template>
  <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" style="overflow:visible">
    <polyline :points="points" fill="none" :stroke="color" stroke-width="2"
      stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>
