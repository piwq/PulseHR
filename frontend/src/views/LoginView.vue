<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AuthAside from '../components/AuthAside.vue'
import PhLogo from '../components/ui/PhLogo.vue'
import PhField from '../components/ui/PhField.vue'
import PhInput from '../components/ui/PhInput.vue'
import PhButton from '../components/ui/PhButton.vue'
import { useAuth } from '../stores/useAuth'

const router = useRouter()
const auth = useAuth()

const step = ref('phone')   // phone | code
const phone = ref('+79990000000')
const code = ref('')
const debugCode = ref('')   // имитация SMS: код приходит в ответе
const loading = ref(false)
const error = ref('')

async function sendCode() {
  error.value = ''
  loading.value = true
  try {
    const res = await auth.requestCode(phone.value)
    debugCode.value = res.debug_code || ''
    code.value = res.debug_code || ''   // в MVP подставляем для удобства демо
    step.value = 'code'
  } catch (e) {
    error.value = e.data?.detail || 'Не удалось отправить код'
  } finally {
    loading.value = false
  }
}

async function confirm() {
  error.value = ''
  loading.value = true
  try {
    await auth.verify(phone.value, code.value)
    router.push(auth.isHr ? '/' : '/me')
  } catch (e) {
    error.value = e.data?.detail || 'Неверный код'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth route">
    <AuthAside />
    <div class="auth__form-wrap">
      <form class="auth__form" @submit.prevent="step === 'phone' ? sendCode() : confirm()">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:26px">
          <PhLogo :mark-size="30" :mark-radius="8" :wordmark-size="18" :gap="10" />
        </div>
        <h1 class="h1" style="margin-bottom:6px">Вход в PulseHR</h1>
        <p class="sm muted" style="margin-bottom:28px">
          Авторизация по номеру телефона — один номер = один аккаунт.
        </p>

        <div style="display:flex;flex-direction:column;gap:16px">
          <PhField label="Номер телефона" html-for="lg-phone">
            <PhInput id="lg-phone" type="tel" icon="user" placeholder="+7 999 000-00-00"
              v-model="phone" :disabled="step === 'code'" />
          </PhField>

          <PhField v-if="step === 'code'" label="Код из SMS" html-for="lg-code"
            :hint="debugCode ? `Демо-режим: код ${debugCode} (имитация SMS)` : undefined">
            <PhInput id="lg-code" type="text" icon="lock" placeholder="6-значный код" v-model="code" />
          </PhField>

          <p v-if="error" class="xs" style="color:var(--sev-crit-text)">{{ error }}</p>

          <PhButton variant="primary" size="lg" block type="submit"
            :icon-right="loading ? undefined : 'arrow'">
            {{ loading ? 'Подождите…' : (step === 'phone' ? 'Получить код' : 'Войти') }}
          </PhButton>

          <a v-if="step === 'code'" class="sm" style="color:var(--accent-text);font-weight:600;cursor:pointer;text-align:center"
            @click="step = 'phone'">← Изменить номер</a>
        </div>

        <p class="xs muted" style="text-align:center;margin-top:24px;line-height:1.5">
          Демо: <b>+79990000000</b> — вход как HR. Любой другой номер — как сотрудник.
        </p>
      </form>
    </div>
  </div>
</template>
