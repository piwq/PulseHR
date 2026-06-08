<script setup>
import PhIcon from './PhIcon.vue'
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  type: { type: String, default: 'text' },
  icon: { type: String, default: undefined },
  placeholder: { type: String, default: undefined },
  id: { type: String, default: undefined },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const show = ref(false)
const isPw = computed(() => props.type === 'password')
const inputType = computed(() => (isPw.value ? (show.value ? 'text' : 'password') : props.type))
const wrapped = computed(() => Boolean(props.icon) || isPw.value)
</script>

<template>
  <div v-if="wrapped" style="position:relative">
    <PhIcon v-if="icon" :name="icon" :size="16"
      style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--text-faint);pointer-events:none" />
    <input :id="id" :type="inputType" class="input" :placeholder="placeholder" :disabled="disabled"
      :value="modelValue" @input="emit('update:modelValue', $event.target.value)"
      :style="{ paddingLeft: icon ? '38px' : undefined, paddingRight: isPw ? '40px' : undefined }" />
    <button v-if="isPw" type="button" tabindex="-1" @click="show = !show"
      style="position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:0;cursor:pointer;color:var(--text-faint);padding:6px;display:grid;place-items:center">
      <PhIcon name="eye" :size="16" />
    </button>
  </div>
  <input v-else :id="id" :type="type" class="input" :placeholder="placeholder" :disabled="disabled"
    :value="modelValue" @input="emit('update:modelValue', $event.target.value)" />
</template>
