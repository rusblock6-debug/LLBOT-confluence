# main.py (ПОЛНАЯ ФИНАЛЬНАЯ ВЕРСИЯ)
from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from services.openai_service import generate_text, LLMError
from services.knowledge_service import KnowledgeService
from services.docx_service import create_docx

load_dotenv()

app = FastAPI(title="Smart Writer API")
ks = KnowledgeService()

class RequestModel(BaseModel):
    query: str

def classify_intent_and_structure(query: str) -> tuple[str, str]:
    """Определяет тип документа и возвращает его структуру."""
    query_lower = query.lower()
    
    if "техническое задание" in query_lower or "тз" in query_lower:
        return ("tz", """
        Создай Техническое Задание (ТЗ) для системы "АСУ ПГР".
        Структура:
        1. Титульный лист
        2. Введение (Назначение и цели)
        3. Основные термины и определения (Глоссарий)
        4. Общие положения (Область применения, нормативные ссылки)
        5. Требования к системе:
           - Функциональные требования (Рудопоток, Учёт буровых работ, Планирование)
           - Нефункциональные требования (Надёжность, Производительность, Совместимость)
           - Требования к данным
           - Требования к интерфейсу
        6. Архитектура системы
        7. Руководство пользователя (основные сценарии)
        8. Приложения (схемы, диаграммы)
        """)
    elif "руководство пользователя" in query_lower or "инструкция" in query_lower:
        return ("manual", """
        Создай Руководство пользователя для системы "АСУ ПГР".
        Структура:
        1. Введение
        2. Начало работы (установка, первый запуск)
        3. Основные функции (описание каждого модуля)
        4. Расширенные возможности
        5. Часто задаваемые вопросы (FAQ)
        6. Поддержка и контакты
        """)
    elif "описание" in query_lower or "обзор" in query_lower:
        return ("description", """
        Создай Описание системы "АСУ ПГР".
        Структура:
        1. Обзор системы
        2. Назначение и цели создания
        3. Основные компоненты и модули
        4. Принципы работы
        5. Ключевые преимущества и отличия
        """)
    elif "регламент" in query_lower or "представление" in query_lower:
        return ("regulation", """
        Создай Регламент работы с системой "АСУ ПГР".
        Структура:
        1. Общие положения
        2. Порядок работы с системой (для разных ролей)
        3. Ответственность сотрудников
        4. Контроль качества данных
        5. Порядок отчетности
        """)
    elif "функциональные требования" in query_lower or "фт" in query_lower:
        return ("functional_requirements", "...")
    elif "регламент тестирования" in query_lower or "тест план" in query_lower:
        return ("test_plan", "...")
    elif "бизнес-процесс" in query_lower or "процесс" in query_lower:
        return ("business_process", "...")
    elif "проектный план" in query_lower or "роадмап" in query_lower or "roadmap" in query_lower:
        return ("project_plan", "...")
    elif "анализ рисков" in query_lower or "риски" in query_lower:
        return ("risk_analysis", "...")
    elif "развертывание" in query_lower or "установка" in query_lower or "деплой" in query_lower:
        return ("deployment_guide", "...")
    else:
        return ("general", "Ответь на вопрос по системе 'АСУ ПГР' на основе предоставленной информации.")

@app.get("/")
def read_root():
    return {"status": "Smart Writer API is running"}

@app.post("/generate")
def generate_documentation(request: RequestModel):
    user_query = request.query
    print(f"\n--- НОВЫЙ ЗАПРОС: {user_query} ---")
    
    try:
        # 1. Ищем релевантный контекст
        relevant_context = ks.search_relevant_knowledge(query=user_query, n_results=7)
        
        # 2. Определяем тип документа и структуру
        intent_type, structure_prompt = classify_intent_and_structure(user_query)
        print(f"Определен тип документа: {intent_type}")

        # 3. Формируем финальный промпт
        prompt = f"""
        Ты — старший технический писатель и бизнес-аналитик с многолетним опытом в горно-металлургической отрасли и промышленной автоматизации. Твоя задача — создать качественный, аналитический документ на основе запроса пользователя и предоставленной базы знаний по системе "АСУ ПГР".

        ЗАПРОС ПОЛЬЗОВАТЕЛЯ: "{user_query}"

        СТРУКТУРА ДОКУМЕНТА:
        {structure_prompt}

        БАЗА ЗНАНИЙ (ОСНОВА ДЛЯ АНАЛИЗА):
        ---
        {relevant_context}
        ---

        ИНСТРУКЦИИ ПО СОЗДАНИЮ:
        1.  **Будь экспертом, а не копировальщиком:** Твоя главная задача — не скопировать, а **проанализировать, синтезировать и создать**. Используй базу знаний как основу, но применяй свой опыт для создания целостного и логичного документа.
        2.  **Заполняй пробелы:** Если для какого-то раздела в базе знаний нет прямых данных, **сделай логическое предположение** на основе общего контекста. Четко укажи, что это предположение (например: "На основе анализа архитектуры можно предположить, что...").
        3.  **Синтезируй информацию:** Соединяй данные из разных частей базы знаний, чтобы создать полную картину.
        4.  **Форматирование:** Используй Markdown для форматирования. Используй заголовки (###, ####), списки (*), **жирный текст**, `код` и таблицы для улучшения читаемости.
        5.  **Пиши профессионально:** Используй терминологию отрасли, пиши четко и по делу.

        Приступай к созданию документа.
        """
        
        # 4. Генерируем текст (здесь может возникнуть ошибка)
        generated_text = generate_text(prompt)
        
        # 5. Создаем DOCX файл (только если текст успешно сгенерирован)
        title = f"Документ: {user_query}"
        docx_path = create_docx(content=generated_text, title=title)
        
        return {"status": "success", "file_path": docx_path}

    except LLMError as e:
        # Ловим нашу ошибку от LLM
        error_message = f"Не удалось сгенерировать текст. Причина: {e}"
        print(error_message)
        return {"status": "error", "message": error_message}
    except Exception as e:
        # Ловим все остальные непредвиденные ошибки
        error_message = f"Произошла непредвиденная ошибка: {e}"
        print(error_message)
        return {"status": "error", "message": error_message}