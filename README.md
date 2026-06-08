# PulseHR — корпоративный сервис опросов сотрудников

MVP по ТЗ ООО «СКС Ломбард»: OTP-авторизация, конструктор опросов с ветвлением, анонимный/
идентифицированный режимы, каскадные уведомления (Web Push → Telegram → SMS → e-mail), eNPS и
аналитика по подразделениям. Монорепо, один Django-проект → несколько контейнеров за nginx.

## Запуск

```bash
cp .env.example .env          # уже есть готовый .env с VAPID-ключами для локали
docker compose up -d --build  # migrate всех приложений + создание суперюзера
docker compose exec core python scripts/seed.py   # демо-данные (опрос, 40 сотрудников, волны)
```

- Веб-приложение: <http://localhost/>
- Django admin (суперюзер `admin`/`admin`): <http://localhost/admin/>

### Демо-аккаунты (вход по OTP — код приходит в ответе/на экране, имитация SMS)
- **HR:** телефон `+79990000000` → дашборд, конструктор, аналитика
- **Сотрудник:** любой другой номер (напр. `+79011007`) → список опросов, прохождение

## Покрытие ТЗ

| Раздел ТЗ | Реализация |
|---|---|
| Авторизация по телефону (OTP), роли HR/Сотрудник, 1 номер = 1 аккаунт, анти-повтор | `apps/accounts` + `Participation` |
| Конструктор опросов: single / multi / scale(NPS) / text / matrix, статусы, сроки, аудитория | `apps/surveys` + `SurveyBuilderView.vue` |
| Ветвление (conditional logic) | `Question.branch_rules` + движок в `SurveyTakeView.vue` |
| Анонимный / идентифицированный режимы | `Survey.mode`, `Response.session_id` vs `employee` |
| Каскадные уведомления Web Push → Telegram → SMS → e-mail, таймеры/дедуп/лимиты/152-ФЗ | `apps/notifications` + `run_dispatcher` |
| Триггеры (публикация, напоминания 48ч/24ч) | `services.enqueue_for_trigger` / `run_scheduler` |
| Настройки каналов сотрудником, устройства, DND | `NotificationSettingsView.vue` + `ChannelPrefs` |
| Метрики доставки (sent/CTR/стоимость SMS) | `GET /api/notifications/delivery/{id}` |
| Аналитика: % прохождения, по отделам, распределение, eNPS, комментарии, по дням, гейт N≥5 | `apps/surveys/analytics.py` |
| Экспорт CSV / XLSX | `GET /api/surveys/{id}/export?fmt=csv|xlsx` |
| AI-анализ текстовых ответов (бонус) | `apps/insights` (`analyze` + LLM-fallback) + SSE-тост |

## Архитектура и осознанные замены

- **Без Redis/Celery** (жёсткое требование): асинхронная рассылка, эскалация по таймерам и расписание —
  **DB-воркер** `run_dispatcher` (поллинг таблицы заданий). Счётчики/дедуп/лимиты — таблицы Postgres.
  Жюри: «target — Celery+Redis, MVP — DB-диспетчер, та же топология сервисов».
- **Каналы:** Web Push (pywebpush + VAPID + Service Worker) и Telegram — живые; **SMS и e-mail —
  имитация-адаптеры** (логируют статус/стоимость/время → каскад и метрики каналов полные без платного
  провайдера; ТЗ допускает «имитацию в MVP»).
- **Сервисы compose:** `db` · `core` (API+admin) · `insights` (gthread, SSE+LLM) · `bot` (TG: алерты +
  привязка `/start`) · `dispatcher` (каскад) · `frontend` (Vue-статика) · `nginx` (gateway :80).
  Один образ `backend` на core/insights/bot/dispatcher — разница в `command`. Миграции гоняет только `core`.

## Демо-сценарий

1. Вход HR (`+79990000000`) → дашборд: вовлечённость, eNPS, тренд по отделам, «Продажи» — critical (гейт N≥5).
2. «Новый опрос» → конструктор: типы вопросов + ветвление + режим + аудитория → «Опубликовать».
3. Публикация запускает каскад: `dispatcher` рассылает уведомления (Web Push → … → SMS), видно в
   «Эффективности каналов» (`delivery`).
4. Вход сотрудником с другого телефона → разрешает Web Push → проходит опрос (ветвление, плашка режима).
5. HR жмёт «Демо-алерт» → AI-анализ свободных ответов → тост на дашборде (SSE) + алерт в Telegram.

> Для быстрой демонстрации эскалации каскада таймеры схлопнуты: `NOTIF_DEMO_SECONDS=20` в `.env`
> (боевые значения ТЗ — 4ч/8ч/7д/24ч — при пустой переменной).

## Полезное

- VAPID-ключи для Web Push: `docker compose exec core python manage.py gen_vapid` → в `.env`.
- SQLite-fallback: заменить `DATABASE_URL` на `sqlite:////app/db.sqlite3`.
- Telegram: задать `TELEGRAM_BOT_TOKEN` + `TELEGRAM_BOT_USERNAME`; сотрудник привязывает чат через
  deep-link в настройках уведомлений (бот ловит `/start <code>`).
