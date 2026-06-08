<script setup>
defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: undefined },
  rows: { type: [Number, String], default: 5 },
})
const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <textarea class="textarea" :rows="rows" :placeholder="placeholder"
    :value="modelValue" @input="emit('update:modelValue', $event.target.value)" />
</template>
