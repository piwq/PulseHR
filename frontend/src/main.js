import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

import './assets/tokens.css'
import './assets/app.css'

const app = createApp(App)
app.use(createPinia()).use(router)
// Восстановление сессии по токену делает router.beforeEach (до первого решения о доступе).
app.mount('#app')
