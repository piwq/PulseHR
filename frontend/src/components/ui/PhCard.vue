<script setup>
import { computed } from 'vue'

const props = defineProps({
  hover: { type: Boolean, default: false },
  pad: { type: Boolean, default: true },
})
const cls = computed(() => ['card', props.hover ? 'card--hover' : ''].filter(Boolean).join(' '))
</script>

<template>
  <div :class="cls">
    <div v-if="pad" class="card__pad"><slot /></div>
    <slot v-else />
  </div>
</template>
