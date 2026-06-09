import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from './layouts/AppLayout.vue'
import { useAuth } from './stores/useAuth'

const routes = [
  { path: '/login', name: 'login', component: () => import('./views/LoginView.vue') },

  // HR-зона (app-shell, только роль hr)
  {
    path: '/',
    component: AppLayout,
    meta: { requiresAuth: true, requiresHr: true },
    children: [
      { path: '', name: 'dashboard', component: () => import('./views/DashboardView.vue'),
        meta: { title: 'Дашборд', sub: 'Аналитика вовлечённости и eNPS', action: null } },
      { path: 'depts', name: 'depts', component: () => import('./views/DeptsView.vue'),
        meta: { title: 'Отделы', sub: 'Вовлечённость и eNPS по командам',
          action: { label: 'Новый отдел', icon: 'trend' } } },
      { path: 'depts/:name', name: 'dept-detail', component: () => import('./views/DeptDetailView.vue'),
        meta: { title: 'Отдел', sub: 'Состав и метрики команды', action: null } },
      { path: 'surveys', name: 'surveys', component: () => import('./views/SurveysView.vue'),
        meta: { title: 'Опросы', sub: 'Конструктор и статусы циклов',
          action: { label: 'Новый опрос', icon: 'survey', path: '/surveys/new' } } },
      { path: 'surveys/new', name: 'survey-new', component: () => import('./views/SurveyBuilderView.vue'),
        meta: { title: 'Новый опрос', sub: 'Конструктор с ветвлением', action: null } },
      { path: 'surveys/:id/edit', name: 'survey-edit', component: () => import('./views/SurveyBuilderView.vue'),
        meta: { title: 'Редактирование опроса', sub: 'Конструктор с ветвлением', action: null } },
      { path: 'employees', name: 'employees', component: () => import('./views/EmployeesView.vue'),
        meta: { title: 'Сотрудники', sub: 'Управление профилями и отделами',
          action: { label: 'Новый сотрудник', icon: 'user' } } },
      { path: 'alerts', name: 'alerts', component: () => import('./views/AlertsView.vue'),
        meta: { title: 'Алерты', sub: 'Сигналы, требующие внимания',
          action: { label: 'Разослать алерт', icon: 'alert' } } },
      { path: 'channels', name: 'channels', component: () => import('./views/ChannelsView.vue'),
        meta: { title: 'Каналы', sub: 'Эффективность доставки уведомлений', action: null } },
      { path: 'comparison', name: 'comparison', component: () => import('./views/ComparisonView.vue'),
        meta: { title: 'Сравнение волн', sub: 'Динамика опросов во времени', action: null } },
      { path: 'ai-report', name: 'ai-report', component: () => import('./views/AiReportView.vue'),
        meta: { title: 'ИИ-отчёт', sub: 'Сводка по опросу от ИИ', action: null } },
      { path: 'history', name: 'history', component: () => import('./views/HistoryView.vue'),
        meta: { title: 'История', sub: 'Прошлые циклы опросов', action: null } },
      { path: 'profile', name: 'profile', component: () => import('./views/ProfileView.vue'),
        meta: { title: 'Мой профиль', sub: 'Личные данные и настройки', action: null } },
    ],
  },

  // Зона сотрудника (без сайдбара)
  { path: '/me', name: 'me', component: () => import('./views/EmployeeHomeView.vue'),
    meta: { requiresAuth: true } },
  { path: '/me/notifications', name: 'me-notifications',
    component: () => import('./views/NotificationSettingsView.vue'), meta: { requiresAuth: true } },

  // Прохождение опроса (любая роль, требует авторизации — анти-повтор + охват)
  { path: '/s/:id', name: 'survey', component: () => import('./views/SurveyTakeView.vue'),
    meta: { requiresAuth: true } },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  const auth = useAuth()
  // Дожидаемся восстановления сессии по токену до решения о доступе (иначе редирект на /login при F5).
  if (!auth.ready) await auth.restore()
  if (to.meta.requiresAuth && !auth.authenticated) return { name: 'login' }
  if (to.meta.requiresHr && !auth.isHr) return { name: 'me' }
  if (to.name === 'login' && auth.authenticated) return { name: auth.isHr ? 'dashboard' : 'me' }
})

export default router
