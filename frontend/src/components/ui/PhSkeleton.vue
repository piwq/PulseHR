<script setup>
defineProps({
  w: { type: [Number, String], default: '100%' },
  h: { type: [Number, String], default: 14 },
  r: { type: [Number, String], default: 7 },
})
function px(v) { return typeof v === 'number' ? v + 'px' : v }
</script>

<template>
  <div class="skeleton" :style="{ width: px(w), height: px(h), borderRadius: px(r) }" />
</template>
