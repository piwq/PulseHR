<script setup>
import PhIcon from './PhIcon.vue'
import { computed } from 'vue'

const props = defineProps({
  variant: { type: String, default: 'primary' }, // primary | secondary | ghost
  size: { type: String, default: undefined },     // 'lg'
  block: { type: Boolean, default: false },
  icon: { type: String, default: undefined },
  iconRight: { type: String, default: undefined },
  disabled: { type: Boolean, default: false },
})

const cls = computed(() => [
  'btn', `btn--${props.variant}`,
  props.size === 'lg' ? 'btn--lg' : '',
  props.block ? 'btn--block' : '',
].filter(Boolean).join(' '))

const iconSize = computed(() => (props.size === 'lg' ? 17 : 15))
</script>

<template>
  <button :class="cls" :disabled="disabled">
    <PhIcon v-if="icon" :name="icon" :size="iconSize" :stroke="1.7" />
    <slot />
    <PhIcon v-if="iconRight" :name="iconRight" :size="iconSize" :stroke="1.7" />
  </button>
</template>
