"""LLM-разбор свободных ответов. STUB — доменка по ТЗ.

В Фазе 2 здесь живёт реальный промпт (YandexGPT / Ollama qwen2.5-coder),
а _fallback остаётся страховкой на случай недоступности LLM на площадке (§8).

Ниже — ИИ-отчёт по опросу (Groq). Провайдеро-зависимый код изолирован в одном
адаптере (_groq_report): смена на YandexGPT/локальную LLM = новый адаптер ~25 строк
+ AI_REPORT_PROVIDER=<name>, без правок endpoint/сбора данных/фронта.
"""
import json
import logging
import os

log = logging.getLogger("insights")


def analyze_texts(texts):
    """Вернуть {"summary": str, "top_themes": list[str], "severity": int}.

    TODO [уточнить по ТЗ]:
      - собрать промпт из текстовых ответов
      - дернуть LLM (LLM_PROVIDER: yandexgpt / ollama)
      - распарсить JSON-ответ модели
    Пока всегда rule-based fallback.
    """
    provider = os.environ.get("LLM_PROVIDER", "fallback")
    if provider == "fallback":
        return _fallback(texts)

    # TODO [уточнить по ТЗ]: реальные вызовы провайдеров.
    return _fallback(texts)


def _fallback(texts):
    """Rule-based страховка без сети.

    TODO [уточнить по ТЗ]:
      - извлечение top_themes (топ-слова из негативных ответов)
      - severity-правила (порог среднего балла / падение к прошлой волне)
    """
    n = len(texts)
    summary = (
        f"[stub] Проанализировано ответов: {n}. "
        "Доменный разбор причин подключается по ТЗ."
    )
    return {"summary": summary, "top_themes": [], "severity": 2}


# ── ИИ-отчёт по опросу ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """Ты — опытный HR-аналитик. На вход ты получаешь JSON с агрегатами \
по одному опросу вовлечённости: метаданные опроса, список вопросов, общие метрики \
(индекс вовлечённости по шкале 1–5, eNPS −100..100, % участия), разбивку по отделам \
с severity, недельный тренд, распределение ответов и обезличенные комментарии.

Пороги «нормы»: индекс вовлечённости < 3.0 — критично, < 3.5 — ниже нормы; \
падение тренда ≥ 0.6 — критично, ≥ 0.3 — внимание; eNPS < 0 — тревожно; \
участие < 60% — низкая репрезентативность. Отделы с n < 5 скрыты (анонимность) — \
не делай по ним выводов.

Проанализируй: что не так с результатами, какие метрики нарушены и в каких отделах, \
а также — корректно ли составлен сам опрос (мало ответов/нет NPS-вопроса/низкое \
участие/несбалансированные вопросы).

Ответь СТРОГО валидным JSON-объектом на русском языке, без markdown, по схеме:
{
  "overall": "2–3 предложения: общая оценка здоровья опроса и ключевой вывод",
  "problem_zones": ["короткий пункт про нарушенную метрику/проблемный отдел", "..."],
  "survey_quality": "2–3 предложения: насколько корректно составлен и проведён опрос",
  "recommendations": ["конкретное действие для HR", "..."]
}
Списки — 2–5 пунктов. Если данных мало — честно скажи об этом, не выдумывай."""

_KEYS = ("overall", "problem_zones", "survey_quality", "recommendations")


def generate_report(context: dict):
    """Сгенерировать ИИ-отчёт. Возвращает (content: dict, model_used: str)."""
    provider = os.environ.get("AI_REPORT_PROVIDER") or os.environ.get("LLM_PROVIDER", "fallback")
    if provider == "groq" and os.environ.get("GROQ_API_KEY"):
        try:
            return _groq_report(context)
        except Exception as e:  # noqa: BLE001 — деградируем до заглушки, не роняем endpoint
            log.warning("groq report failed, fallback: %s", e)
    return _fallback_report(context)


def _groq_report(context: dict):
    from groq import Groq

    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    content = json.loads(resp.choices[0].message.content)
    return _normalize(content), model


def _normalize(content: dict):
    """Привести ответ модели к фикс-схеме (страховка от пропусков/типов)."""
    return {
        "overall": str(content.get("overall") or "").strip(),
        "problem_zones": [str(x).strip() for x in (content.get("problem_zones") or []) if str(x).strip()],
        "survey_quality": str(content.get("survey_quality") or "").strip(),
        "recommendations": [str(x).strip() for x in (content.get("recommendations") or []) if str(x).strip()],
    }


def _fallback_report(context: dict):
    """Rule-based отчёт из самих метрик — работает без сети/ключа."""
    o = context.get("overall", {}) or {}
    eng, enps, part = o.get("engagement"), o.get("enps"), o.get("participation")
    resp_n = o.get("responses", 0)

    problems = []
    if eng is not None and eng < 3.0:
        problems.append(f"Критически низкая вовлечённость: {eng} (норма ≥ 3.5).")
    elif eng is not None and eng < 3.5:
        problems.append(f"Вовлечённость ниже нормы: {eng}.")
    if enps is not None and enps < 0:
        problems.append(f"Отрицательный eNPS: {enps}.")
    if part is not None and part < 60:
        problems.append(f"Низкое участие: {part}% — данные слабо репрезентативны.")
    for d in context.get("departments", []):
        if d.get("sev") == "critical":
            problems.append(f"Отдел «{d.get('department')}»: критический сигнал ({d.get('note')}).")

    quality = []
    if resp_n < 5:
        quality.append("Слишком мало ответов для надёжных выводов.")
    if not context.get("has_nps_question"):
        quality.append("В опросе нет NPS-вопроса — eNPS не рассчитывается.")
    if part is not None and part < 60:
        quality.append("Низкий охват аудитории.")

    recs = []
    for d in context.get("departments", []):
        if d.get("sev") in ("critical", "medium"):
            recs.append(f"Провести встречу 1:1 с командой отдела «{d.get('department')}».")
    if not context.get("has_nps_question"):
        recs.append("Добавить шкальный NPS-вопрос для расчёта eNPS.")
    if part is not None and part < 60:
        recs.append("Усилить напоминания, чтобы поднять участие выше 60%.")

    overall = (
        f"Получено {resp_n} ответов. Вовлечённость "
        f"{'—' if eng is None else eng}, eNPS {'—' if enps is None else enps}, "
        f"участие {'—' if part is None else str(part) + '%'}. "
        + ("Есть зоны, требующие внимания." if problems else "Серьёзных отклонений не выявлено.")
    )
    return {
        "overall": overall,
        "problem_zones": problems or ["Явных проблем по метрикам не обнаружено."],
        "survey_quality": " ".join(quality) or "Опрос составлен корректно, данных достаточно.",
        "recommendations": recs or ["Продолжать мониторинг в следующих волнах опроса."],
    }, "fallback"
