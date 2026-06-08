<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: null },
  lowLabel: { type: String, default: 'Совсем нет' },
  highLabel: { type: String, default: 'Полностью да' },
  size: { type: Number, default: 62 },
})
const emit = defineEmits(['update:modelValue'])

const hover = ref(0)
function cls(n) {
  return [
    'scale__btn',
    props.modelValue === n ? 'sel' : '',
    hover.value && n <= hover.value && !props.modelValue ? 'hov' : '',
  ].filter(Boolean).join(' ')
}
</script>

<template>
  <div>
    <div class="scale" @mouseleave="hover = 0">
      <button v-for="n in 5" :key="n" type="button" :class="cls(n)"
        :style="{ width: size + 'px', height: size + 'px' }"
        @mouseenter="hover = n" @click="emit('update:modelValue', n)"
        :aria-label="`Оценка ${n}`">{{ n }}</button>
    </div>
    <div class="scale__ends"><span>{{ lowLabel }}</span><span>{{ highLabel }}</span></div>
  </div>
</template>
