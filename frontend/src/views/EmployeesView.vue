<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import PhCard from '../components/ui/PhCard.vue'
import PhButton from '../components/ui/PhButton.vue'
import PhEmptyState from '../components/ui/PhEmptyState.vue'
import PhSkeleton from '../components/ui/PhSkeleton.vue'
import PhModal from '../components/ui/PhModal.vue'
import { api } from '../lib/api'
import { useAppAction } from '../stores/useAppAction'

const employees = ref([])
const departments = ref([])
const loading = ref(true)
const editing = ref(null)  // { id, name, department, role }
const saving = ref(false)
const search = ref('')

onMounted(async () => {
  loading.value = true
  try {
    ;[employees.value, departments.value] = await Promise.all([
      api('/auth/employees'),
      api('/auth/departments'),
    ])
  } finally {
    loading.value = false }
})

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return employees.value
  return employees.value.filter(
    (e) => (e.name + e.phone + e.department).toLowerCase().includes(q),
  )
})

// Group by department for display
const grouped = computed(() => {
  const groups = {}
  for (const e of filtered.value) {
    const d = e.department || '—'
    if (!groups[d]) groups[d] = []
    groups[d].push(e)
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
})

function startEdit(emp) {
  editing.value = { id: emp.id, name: emp.name, department: emp.department, role: emp.role }
}
function cancelEdit() { editing.value = null }

async function saveEdit() {
  if (!editing.value) return
  saving.value = true
  try {
    const updated = await api(`/auth/employees/${editing.value.id}`, {
      method: 'PATCH',
      body: {
        name: editing.value.name,
        department: editing.value.department,
        role: editing.value.role,
      },
    })
    const idx = employees.value.findIndex((e) => e.id === updated.id)
    if (idx >= 0) employees.value[idx] = updated
    // refresh departments list
    departments.value = [...new Set([...departments.value, updated.department].filter(Boolean))].sort()
    editing.value = null
  } finally {
    saving.value = false
  }
}

const deptOptions = computed(() => {
  const all = [...new Set([...departments.value, ...(editing.value?.department ? [editing.value.department] : [])])]
  return all.filter(Boolean).sort()
})

// Модалка «Новый сотрудник»
const newModal = ref(false)
const newPhone = ref('')
const newName = ref('')
const newDept = ref('')
const newRole = ref('employee')
const newSaving = ref(false)

const appAction = useAppAction()
watch(() => appAction.trigger, () => {
  newModal.value = true
  newPhone.value = ''; newName.value = ''; newDept.value = ''; newRole.value = 'employee'
})

async function createEmployee() {
  if (!newPhone.value.trim()) return
  newSaving.value = true
  try {
    const emp = await api('/auth/employees', {
      method: 'POST',
      body: {
        phone: newPhone.value.trim(),
        name: newName.value.trim(),
        department: newDept.value.trim(),
        role: newRole.value,
      },
    })
    // Добавить/обновить в списке
    const idx = employees.value.findIndex((e) => e.id === emp.id)
    if (idx >= 0) employees.value[idx] = emp
    else employees.value.push(emp)
    if (emp.department && !departments.value.includes(emp.department)) {
      departments.value = [...departments.value, emp.department].sort()
    }
    newModal.value = false
  } finally {
    newSaving.value = false
  }
}
</script>

<template>
  <div class="route" style="display:flex;flex-direction:column;gap:16px">

    <PhCard v-if="loading">
      <PhSkeleton w="100%" :h="20" v-for="i in 5" :key="i" :style="{ marginBottom: '10px' }" />
    </PhCard>

    <template v-else>
      <!-- Поиск + счётчик -->
      <div style="display:flex;gap:10px;align-items:center">
        <input class="input" v-model="search" placeholder="Поиск по имени, телефону, отделу…"
          style="max-width:320px;font-size:13px" />
        <span class="xs muted">{{ employees.length }} сотрудников · {{ departments.length }} отделов</span>
      </div>

      <PhCard v-if="filtered.length === 0">
        <PhEmptyState icon="user" title="Сотрудников нет" body="Пока никто не входил в систему." />
      </PhCard>

      <!-- Таблица сгруппирована по отделам -->
      <PhCard v-for="([dept, emps]) in grouped" :key="dept" :pad="false">
        <div style="padding:10px 16px 6px;display:flex;align-items:center;gap:8px">
          <div class="xs muted" style="font-weight:700;text-transform:uppercase;letter-spacing:.06em">{{ dept }}</div>
          <div class="xs muted">{{ emps.length }}</div>
        </div>
        <table class="tbl">
          <thead>
            <tr>
              <th>Имя / телефон</th>
              <th>Отдел</th>
              <th>Роль</th>
              <th style="text-align:right"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in emps" :key="e.id">
              <template v-if="editing?.id === e.id">
                <td>
                  <input class="input" v-model="editing.name" placeholder="Имя"
                    style="font-size:13px;padding:4px 8px;width:160px" />
                </td>
                <td>
                  <div style="display:flex;gap:6px;align-items:center">
                    <select class="select" v-model="editing.department" style="font-size:13px;padding:4px 8px;min-width:130px">
                      <option value="">— без отдела —</option>
                      <option v-for="d in deptOptions" :key="d" :value="d">{{ d }}</option>
                    </select>
                    <input class="input" v-model="editing.department" placeholder="или введите"
                      style="font-size:13px;padding:4px 8px;width:130px" />
                  </div>
                </td>
                <td>
                  <select class="select" v-model="editing.role" style="font-size:13px;padding:4px 8px">
                    <option value="employee">Сотрудник</option>
                    <option value="hr">HR</option>
                  </select>
                </td>
                <td style="text-align:right">
                  <div style="display:flex;gap:6px;justify-content:flex-end">
                    <PhButton variant="primary" @click="saveEdit" :disabled="saving">{{ saving ? '…' : 'Сохранить' }}</PhButton>
                    <PhButton variant="ghost" @click="cancelEdit">Отмена</PhButton>
                  </div>
                </td>
              </template>
              <template v-else>
                <td>
                  <div style="font-weight:600">{{ e.name || '—' }}</div>
                  <div class="xs muted">{{ e.phone }}</div>
                </td>
                <td class="muted">{{ e.department || '—' }}</td>
                <td>
                  <span class="badge" :class="e.role === 'hr' ? 'badge--low' : 'badge--neutral'">
                    <span class="badge__dot" />{{ e.role === 'hr' ? 'HR' : 'Сотрудник' }}
                  </span>
                </td>
                <td style="text-align:right">
                  <PhButton variant="ghost" @click="startEdit(e)">Изменить</PhButton>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </PhCard>
    </template>

  </div>

  <PhModal :open="newModal" title="Новый сотрудник" @close="newModal = false">
    <div style="display:flex;flex-direction:column;gap:10px">
      <p class="sm muted">Сотрудник получит доступ когда войдёт по этому номеру через OTP.</p>
      <input class="input" v-model="newPhone" placeholder="Телефон (обязательно)" style="font-size:14px" />
      <input class="input" v-model="newName" placeholder="Имя" style="font-size:14px" />
      <select class="select" v-model="newDept" style="font-size:14px">
        <option value="">— без отдела —</option>
        <option v-for="d in deptOptions" :key="d" :value="d">{{ d }}</option>
      </select>
      <input class="input" v-model="newDept" placeholder="Или введите отдел вручную" style="font-size:14px" />
      <select class="select" v-model="newRole" style="font-size:14px">
        <option value="employee">Сотрудник</option>
        <option value="hr">HR</option>
      </select>
    </div>
    <template #footer>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <PhButton variant="ghost" @click="newModal = false">Отмена</PhButton>
        <PhButton variant="primary" :disabled="!newPhone.trim() || newSaving" @click="createEmployee">
          {{ newSaving ? 'Создание…' : 'Создать' }}
        </PhButton>
      </div>
    </template>
  </PhModal>
</template>
