<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  to: { type: Number, required: true },
  dec: { type: Number, default: 0 },
  plus: { type: Boolean, default: false },
  dur: { type: Number, default: 1100 },
})

const val = ref(0)
let raf = null
let fallback = null

onMounted(() => {
  const t0 = performance.now()
  const step = (now) => {
    const p = Math.min(1, (now - t0) / props.dur)
    const e = 1 - Math.pow(1 - p, 3) // ease-out cubic
    val.value = props.to * e
    if (p < 1) raf = requestAnimationFrame(step)
    else val.value = props.to
  }
  raf = requestAnimationFrame(step)
  // clock-independent fallback: guarantee final value even if rAF is throttled/frozen
  fallback = setTimeout(() => { val.value = props.to }, props.dur + 120)
})
onBeforeUnmount(() => { cancelAnimationFrame(raf); clearTimeout(fallback) })
</script>

<template>
  <span class="tnum">{{ (plus && to > 0 ? '+' : '') + val.toFixed(dec) }}</span>
</template>
