<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },   // пусто = «все»
  options:    { type: Array, default: () => [] },
  allLabel:   { type: String, default: 'Все' },
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const root = ref(null)
// Локальный черновик: меняется по чекбоксам, применяется ОДИН раз при закрытии.
const draft = ref([...props.modelValue])

watch(() => props.modelValue, (v) => { if (!open.value) draft.value = [...v] })

const isAll = computed(() => draft.value.length === 0)
const someChecked = computed(() => draft.value.length > 0 && draft.value.length < props.options.length)

function isChecked(o) { return isAll.value || draft.value.includes(o) }

function toggle(o) {
  if (isAll.value) {
    draft.value = props.options.filter(x => x !== o)          // «все» → снять один → выбрать остальные
  } else if (draft.value.includes(o)) {
    draft.value = draft.value.filter(x => x !== o)
  } else {
    const next = [...draft.value, o]
    draft.value = next.length === props.options.length ? [] : next  // выбраны все → «все»
  }
}

function toggleAll() {
  draft.value = isAll.value ? [...props.options] : []
}

function changed() {
  const a = [...draft.value].sort(), b = [...props.modelValue].sort()
  return a.length !== b.length || a.some((x, i) => x !== b[i])
}

function openMenu() { draft.value = [...props.modelValue]; open.value = true }
function close(apply = true) {
  if (!open.value) return
  open.value = false
  if (apply && changed()) emit('update:modelValue', draft.value)
  else draft.value = [...props.modelValue]
}
function toggleMenu() { open.value ? close() : openMenu() }

const label = computed(() => {
  const src = open.value ? draft.value : props.modelValue
  if (src.length === 0) return props.allLabel
  if (src.length === 1) return src[0]
  return `${src.length} выбр.`
})

function onDocClick(e) { if (root.value && !root.value.contains(e.target)) close() }
onMounted(() => document.addEventListener('mousedown', onDocClick))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocClick))
</script>

<template>
  <div ref="root" style="position:relative">
    <button class="ms-btn" :class="(open ? !isAll : modelValue.length) && 'ms-btn--active'" @click="toggleMenu">
      {{ label }}
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 3.5l3 3 3-3"/></svg>
    </button>
    <div v-if="open" class="ms-menu">
      <div class="ms-all" @click="toggleAll">
        <input type="checkbox" :checked="isAll" :indeterminate="someChecked" readonly />
        <span>{{ isAll ? allLabel : 'Снять выбор' }}</span>
      </div>
      <div class="ms-sep" />
      <div class="ms-list">
        <label v-for="o in options" :key="o" class="ms-item">
          <input type="checkbox" :checked="isChecked(o)" @change="toggle(o)" />
          <span>{{ o }}</span>
        </label>
      </div>
      <div class="ms-sep" />
      <div class="ms-foot">
        <button class="ms-apply" @click="close()">Применить</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ms-btn {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid var(--line); border-radius: 8px; background: var(--bg-raised);
  font-size: 12px; font-family: inherit; color: var(--text-secondary);
  padding: 6px 12px; cursor: pointer; white-space: nowrap; height: 30px;
  transition: color .12s, border-color .12s;
}
.ms-btn:hover { border-color: var(--text-faint); color: var(--text); }
.ms-btn--active { color: var(--accent-text, var(--accent)); border-color: var(--accent); background: var(--accent-soft, color-mix(in srgb, var(--accent) 12%, transparent)); }
.ms-menu {
  position: absolute; top: calc(100% + 5px); left: 0; z-index: 400;
  background: var(--bg-base); border: 1px solid var(--line-strong, var(--line));
  border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,.35);
  min-width: 200px; padding: 6px 0;
}
.ms-list { max-height: 220px; overflow-y: auto; }
.ms-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px; cursor: pointer; font-size: 12px; color: var(--text);
  transition: background .1s;
}
.ms-item:hover { background: var(--bg-raised); }
.ms-item input[type=checkbox] { accent-color: var(--accent); width: 13px; height: 13px; flex: none; }
.ms-all {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px; cursor: pointer; font-size: 12px;
  font-weight: 600; color: var(--text-secondary); transition: background .1s;
}
.ms-all:hover { background: var(--bg-raised); }
.ms-all input[type=checkbox] { accent-color: var(--accent); width: 13px; height: 13px; flex: none; pointer-events: none; }
.ms-sep { height: 1px; background: var(--line); margin: 2px 0; }
.ms-foot { padding: 6px 10px 2px; }
.ms-apply {
  width: 100%; padding: 7px 0; border-radius: 7px; border: none; cursor: pointer;
  background: var(--accent); color: #fff; font-family: inherit; font-size: 12px; font-weight: 600;
  transition: opacity .12s;
}
.ms-apply:hover { opacity: .9; }
</style>
