import { ref } from 'vue'
import { defineStore } from 'pinia'

// Единственный канал связи AppLayout → текущий вид.
// AppLayout вызывает fire(), вид наблюдает за trigger и открывает свою модалку.
export const useAppAction = defineStore('appAction', () => {
  const trigger = ref(0)
  function fire() { trigger.value++ }
  return { trigger, fire }
})
