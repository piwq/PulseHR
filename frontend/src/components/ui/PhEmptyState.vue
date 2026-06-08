<script setup>
import PhIcon from './PhIcon.vue'

defineProps({
  icon: { type: String, default: 'survey' },
  title: { type: String, required: true },
  body: { type: String, default: undefined },
})
</script>

<template>
  <div style="text-align:center;padding:48px 24px;max-width:380px;margin:0 auto">
    <div style="width:52px;height:52px;border-radius:14px;margin:0 auto 16px;display:grid;place-items:center;background:var(--bg-surface-2);border:1px solid var(--line);color:var(--text-muted)">
      <PhIcon :name="icon" :size="22" />
    </div>
    <div class="h3" style="margin-bottom:6px">{{ title }}</div>
    <p v-if="body" class="sm muted" :style="{ marginBottom: $slots.action ? '18px' : '0' }">{{ body }}</p>
    <slot name="action" />
  </div>
</template>
