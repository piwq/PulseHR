<script setup>
import PhIcon from './PhIcon.vue'
import { watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: undefined },
  width: { type: Number, default: 440 },
})
const emit = defineEmits(['close'])

function onKey(e) { if (e.key === 'Escape') emit('close') }
watch(() => props.open, (v) => {
  if (v) window.addEventListener('keydown', onKey)
  else window.removeEventListener('keydown', onKey)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-overlay" @mousedown.self="emit('close')">
      <div class="modal" :style="{ maxWidth: width + 'px' }" @mousedown.stop>
        <div class="modal__head">
          <div class="h3">{{ title }}</div>
          <button class="iconbtn" style="width:30px;height:30px" @click="emit('close')">
            <PhIcon name="x" :size="15" />
          </button>
        </div>
        <div class="modal__body"><slot /></div>
        <div v-if="$slots.footer" class="modal__foot"><slot name="footer" /></div>
      </div>
    </div>
  </Teleport>
</template>
