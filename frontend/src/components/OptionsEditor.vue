<script setup>
import PhInput from './ui/PhInput.vue'
import PhIcon from './ui/PhIcon.vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Вариант' },
  addLabel: { type: String, default: 'Добавить вариант' },
})
const emit = defineEmits(['update:modelValue'])

function update(i, val) { const a = [...props.modelValue]; a[i] = val; emit('update:modelValue', a) }
function add() { emit('update:modelValue', [...props.modelValue, '']) }
function remove(i) { const a = [...props.modelValue]; a.splice(i, 1); emit('update:modelValue', a) }
function move(i, dir) {
  const a = [...props.modelValue]; const j = i + dir
  if (j < 0 || j >= a.length) return
  ;[a[i], a[j]] = [a[j], a[i]]; emit('update:modelValue', a)
}
</script>

<template>
  <div>
    <div style="display:flex;flex-direction:column;gap:8px">
      <div v-for="(opt, i) in modelValue" :key="i" style="display:flex;align-items:center;gap:8px">
        <span class="mono xs" style="color:var(--text-faint);width:16px;text-align:right">{{ i + 1 }}</span>
        <PhInput :model-value="opt" @update:model-value="update(i, $event)" :placeholder="placeholder" style="flex:1" />
        <button class="iconbtn" style="width:30px;height:30px" @click="move(i, -1)" title="Вверх"><PhIcon name="up" :size="13" /></button>
        <button class="iconbtn" style="width:30px;height:30px" @click="move(i, 1)" title="Вниз"><PhIcon name="down" :size="13" /></button>
        <button class="iconbtn" style="width:30px;height:30px" @click="remove(i)" title="Удалить"><PhIcon name="x" :size="13" /></button>
      </div>
    </div>
    <button type="button" class="btn btn--ghost" style="margin-top:10px" @click="add">
      <PhIcon name="grid" :size="14" />{{ addLabel }}
    </button>
  </div>
</template>
