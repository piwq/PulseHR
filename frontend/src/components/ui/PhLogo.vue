<script setup>
// Brand mark (ЭКГ/пульс-линия в изумруде) + wordmark PulseHR.
defineProps({
  markSize: { type: Number, default: 32 },
  markRadius: { type: Number, default: 9 },
  wordmarkSize: { type: Number, default: 17 },
  gap: { type: Number, default: 11 },
})
</script>

<template>
  <span :style="{ display: 'inline-flex', alignItems: 'center', gap: gap + 'px' }">
    <svg :width="markSize" :height="markSize" viewBox="0 0 40 40" fill="none"
         style="flex:none" aria-hidden="true">
      <rect width="40" height="40" :rx="markRadius" fill="oklch(0.62 0.11 165)" />
      <polyline points="7,21 13,21 16,12 21,29 25,21 33,21" fill="none"
                stroke="oklch(0.16 0.02 165)" stroke-width="2.4"
                stroke-linecap="round" stroke-linejoin="round" />
    </svg>
    <span :style="{ fontSize: wordmarkSize + 'px', fontWeight: 800, letterSpacing: '-0.02em' }">
      Pulse<span style="color:var(--accent-text)">HR</span>
    </span>
  </span>
</template>
