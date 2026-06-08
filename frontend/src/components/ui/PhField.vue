<script setup>
defineProps({
  label: { type: String, default: undefined },
  hint: { type: String, default: undefined },
  error: { type: String, default: undefined },
  htmlFor: { type: String, default: undefined },
})
</script>

<template>
  <div class="field">
    <label v-if="label" class="label" :for="htmlFor">{{ label }}</label>
    <slot />
    <span v-if="error" class="xs" style="color:var(--sev-crit-text)">{{ error }}</span>
    <span v-else-if="hint" class="xs muted">{{ hint }}</span>
  </div>
</template>
