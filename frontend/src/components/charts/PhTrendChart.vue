<script setup>
import { computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  series: { type: Array, required: true },
  labels: { type: Array, required: true },
  min: { type: Number, default: null },
  max: { type: Number, default: null },
  width: { type: Number, default: 640 },
  height: { type: Number, default: 230 },
  padL: { type: Number, default: 40 },
  padR: { type: Number, default: 12 },
  padT: { type: Number, default: 20 },
  padB: { type: Number, default: 30 },
  animate: { type: Boolean, default: true },
})

const allVals = computed(() =>
  props.series.flatMap((s) => s.values.filter((v) => v != null)),
)

const eMin = computed(() => {
  if (props.min != null) return props.min
  if (!allVals.value.length) return 1
  return Math.floor((Math.min(...allVals.value) - 0.25) * 2) / 2
})
const eMax = computed(() => {
  if (props.max != null) return props.max
  if (!allVals.value.length) return 5
  return Math.ceil((Math.max(...allVals.value) + 0.25) * 2) / 2
})
const yTicks = computed(() => {
  const ticks = []
  const step = (eMax.value - eMin.value) > 3 ? 1 : 0.5
  for (let v = eMax.value; v >= eMin.value - 0.01; v -= step) {
    ticks.push(Math.round(v * 10) / 10)
  }
  return ticks
})

const bottom = computed(() => props.height - props.padB)

function scaleY(v) {
  const range = eMax.value - eMin.value || 1
  const t = (v - eMin.value) / range
  return bottom.value - t * (bottom.value - props.padT)
}
function xAt(i) {
  const innerW = props.width - props.padL - props.padR
  const steps = Math.max(props.labels.length - 1, 1)
  return props.padL + i * (innerW / steps)
}
function pointsFor(s) {
  return s.values
    .map((v, i) => (v != null ? `${xAt(i)},${scaleY(v)}` : null))
    .filter(Boolean)
    .join(' ')
}

const lineEls = []
function setLine(i, el) { if (el) lineEls[i] = el }

let timers = []
onMounted(() => {
  if (!props.animate) return
  lineEls.forEach((p, idx) => {
    if (!p) return
    const len = p.getTotalLength()
    p.style.transition = 'none'
    p.style.strokeDasharray = len
    p.style.strokeDashoffset = len
    p.getBoundingClientRect()
    p.style.transition = `stroke-dashoffset 900ms cubic-bezier(0.22,0.61,0.36,1) ${idx * 90}ms`
    p.style.strokeDashoffset = '0'
    timers.push(setTimeout(() => {
      if (p) { p.style.transition = 'none'; p.style.strokeDashoffset = '0' }
    }, 1100 + idx * 90))
  })
})
onBeforeUnmount(() => timers.forEach(clearTimeout))
</script>

<template>
  <svg :viewBox="`0 0 ${width} ${height}`" width="100%" preserveAspectRatio="none" style="overflow:visible">
    <g stroke="var(--line)" stroke-width="1">
      <line v-for="(t, i) in yTicks" :key="'g' + i" :x1="padL" :y1="scaleY(t)" :x2="width - padR" :y2="scaleY(t)" />
    </g>
    <g font-family="var(--font-mono)" font-size="9.5" fill="var(--text-faint)">
      <text v-for="(t, i) in yTicks" :key="'yt' + i" :x="8" :y="scaleY(t) + 4">{{ t.toFixed(1) }}</text>
    </g>
    <polyline v-for="(s, si) in series" :key="s.key" :ref="el => setLine(si, el)"
      :points="pointsFor(s)" fill="none" :stroke="s.color"
      :stroke-width="s.emphasis ? 2.6 : 1.6" :stroke-opacity="s.emphasis ? 1 : 0.55"
      stroke-linecap="round" stroke-linejoin="round" />
    <template v-for="s in series.filter(s => s.emphasis)" :key="'d' + s.key">
      <circle v-if="s.values.at(-1) != null"
        :cx="xAt(s.values.length - 1)" :cy="scaleY(s.values.at(-1))"
        :r="s.crit ? 4 : 3.5" :fill="s.color" />
    </template>
    <g font-family="var(--font-mono)" font-size="10" fill="var(--text-muted)" text-anchor="middle">
      <text v-for="(l, i) in labels" :key="'x' + i" :x="xAt(i)" :y="height - 8">{{ l }}</text>
    </g>
  </svg>
</template>
