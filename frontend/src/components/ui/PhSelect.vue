<script setup>
defineProps({
  modelValue: { type: [String, Number], default: '' },
})
const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <select class="select" :value="modelValue" @change="emit('update:modelValue', $event.target.value)">
    <slot />
  </select>
</template>
