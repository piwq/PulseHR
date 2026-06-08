<script setup>
import PhLogo from './ui/PhLogo.vue'
</script>

<template>
  <div class="auth__aside">
    <PhLogo :mark-size="36" :mark-radius="10" :wordmark-size="21" :gap="12" />
    <div>
      <svg class="pulse-deco" viewBox="0 0 600 80" width="100%" height="80" fill="none" aria-hidden="true">
        <path d="M0,40 L120,40 L150,40 L168,16 L196,64 L214,40 L300,40 L330,40 L348,22 L376,58 L394,40 L520,40 L600,40"
          stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <p class="auth-quote">Замечайте сигналы раньше, чем они станут проблемой.</p>
      <div class="auth__stat">
        <div><div class="v">3 мин</div><div class="k">на опрос сотрудника</div></div>
        <div><div class="v">100%</div><div class="k">анонимно</div></div>
      </div>
    </div>
  </div>
</template>
