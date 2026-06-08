<script setup>
import { computed } from 'vue'
import PhTextarea from './ui/PhTextarea.vue'
import PhIcon from './ui/PhIcon.vue'

const props = defineProps({
  question: { type: Object, required: true },
  modelValue: { default: null },
})
const emit = defineEmits(['update:modelValue'])

const cfg = computed(() => props.question.config || {})
const options = computed(() => cfg.value.options || [])
const scaleRange = computed(() => {
  const min = cfg.value.min ?? 1
  const max = cfg.value.max ?? 5
  return Array.from({ length: max - min + 1 }, (_, i) => min + i)
})
const scaleSize = computed(() => (scaleRange.value.length > 6 ? 44 : 60))

function toggleMulti(opt) {
  const arr = Array.isArray(props.modelValue) ? [...props.modelValue] : []
  const i = arr.indexOf(opt)
  if (i >= 0) arr.splice(i, 1); else arr.push(opt)
  emit('update:modelValue', arr)
}
function setMatrix(row, col) {
  emit('update:modelValue', { ...(props.modelValue || {}), [row]: col })
}
</script>

<template>
  <!-- scale / NPS -->
  <div v-if="question.qtype === 'scale'">
    <div class="scale" style="flex-wrap:wrap">
      <button v-for="n in scaleRange" :key="n" type="button"
        class="scale__btn" :class="{ sel: modelValue === n }"
        :style="{ width: scaleSize + 'px', height: scaleSize + 'px' }"
        @click="emit('update:modelValue', n)">{{ n }}</button>
    </div>
    <div v-if="cfg.low || cfg.high" class="scale__ends">
      <span>{{ cfg.low || '' }}</span><span>{{ cfg.high || '' }}</span>
    </div>
  </div>

  <!-- single choice -->
  <div v-else-if="question.qtype === 'single'" style="max-width:440px;margin:0 auto;display:flex;flex-direction:column;gap:10px">
    <button v-for="o in options" :key="o" type="button" class="choice"
      :class="{ sel: modelValue === o }" @click="emit('update:modelValue', o)">{{ o }}</button>
  </div>

  <!-- multiple choice -->
  <div v-else-if="question.qtype === 'multi'" style="max-width:440px;margin:0 auto;display:flex;flex-direction:column;gap:10px">
    <button v-for="o in options" :key="o" type="button" class="choice"
      :class="{ sel: Array.isArray(modelValue) && modelValue.includes(o) }" @click="toggleMulti(o)">
      <span class="choice__box">
        <PhIcon v-if="Array.isArray(modelValue) && modelValue.includes(o)" name="check" :size="12" :stroke="2.6" />
      </span>{{ o }}
    </button>
  </div>

  <!-- text -->
  <div v-else-if="question.qtype === 'text'" style="max-width:480px;margin:0 auto">
    <PhTextarea :rows="5" placeholder="Напишите ответ…" :model-value="modelValue || ''"
      @update:model-value="emit('update:modelValue', $event)" style="text-align:left" />
  </div>

  <!-- matrix -->
  <table v-else-if="question.qtype === 'matrix'" class="matrix">
    <thead>
      <tr><th></th><th v-for="c in (cfg.cols || [])" :key="c">{{ c }}</th></tr>
    </thead>
    <tbody>
      <tr v-for="r in (cfg.rows || [])" :key="r">
        <td class="matrix__row">{{ r }}</td>
        <td v-for="c in (cfg.cols || [])" :key="c" style="text-align:center">
          <input type="radio" :name="'m' + question.id + r" :checked="(modelValue || {})[r] === c"
            @change="setMatrix(r, c)" style="accent-color:var(--accent);width:16px;height:16px" />
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.choice {
  font-family: inherit; font-size: 15px; text-align: left; padding: 13px 16px;
  border-radius: var(--r-md); border: 1px solid var(--line-strong);
  background: var(--bg-surface); color: var(--text); cursor: pointer;
  display: flex; align-items: center; gap: 10px;
  transition: border-color var(--t-fast) var(--ease), background var(--t-fast) var(--ease);
}
.choice:hover { border-color: var(--text-faint); }
.choice.sel { border-color: var(--accent); background: var(--accent-soft); color: var(--accent-text); }
.choice__box { width: 18px; height: 18px; border-radius: 5px; border: 1.5px solid currentColor; flex: none; display: grid; place-items: center; }
.choice.sel .choice__box { background: var(--accent); border-color: var(--accent); color: var(--accent-on); }
.matrix { margin: 0 auto; border-collapse: collapse; }
.matrix th { font-size: 12px; color: var(--text-muted); font-weight: 600; padding: 6px 12px; }
.matrix td { padding: 8px 12px; border-top: 1px solid var(--line); }
.matrix__row { text-align: left; font-size: 14px; }
</style>
