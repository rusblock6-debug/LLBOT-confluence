# main.py (ВЕРСИЯ С ЖЕСТКИМ ПОШАГОВЫМ ПРОМТОМ ДЛЯ ШАБЛОНОВ)
from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Для чтения .docx файлов
try:
    from docx import Document
except ImportError:
    print("ОШИБКА: Библиотека 'python-docx' не найдена. Выполните 'pip install python-docx'")
    # Создаем фиктивный класс, чтобы не сломался импорт
    class Document: pass

from services.openai_service import generate_text, LLMError
from services.knowledge_service import KnowledgeService
from services.docx_service import create_docx

load_dotenv()

# --- Инициализация ---
app = FastAPI(title="Smart Writer API")
ks = KnowledgeService()

# --- Pydantic Модели для запросов ---

class RequestModel(BaseModel):
    query: str

class TermRequestModel(BaseModel):
    term: str

class ProcessRequestModel(BaseModel):
    query: str
    request_type: str  # "document" или "term"
    template_name: str = None # Имя файла шаблона, например "ГОСТ34_Техническое задание.doc"

# --- Вспомогательные функции ---

def classify_intent_and_structure(query: str) -> tuple[str, str]:
    """Определяет тип документа и возвращает его универсальную структуру."""
    # Эта функция теперь используется только если шаблон НЕ указан
    query_lower = query.lower()
    
    if "техническое задание" in query_lower or "тз" in query_lower:
        return ("tz", "Создай Техническое Задание.")
    elif "руководство пользователя" in query_lower or "инструкция" in query_lower:
        return ("manual", "Создай Руководство пользователя.")
    else:
        return ("general", "Создай документ на основе запроса.")

def get_term_definition_from_knowledge(term: str) -> str:
    """Ищет определение термина в базе знаний с помощью семантического поиска."""
    search_query = f"определение термина {term}"
    relevant_context = ks.search_relevant_knowledge(query=search_query, n_results=1)
    
    if not relevant_context or "не найдена" in relevant_context:
        return None
    return relevant_context

def read_template_file(template_name: str) -> str:
    """Читает файл шаблона (.docx) и возвращает его текстовое содержимое."""
    if not template_name:
        return ""
    
    template_path = os.path.join("templates", template_name)
    
    if not os.path.exists(template_path):
        print(f"Шаблон не найден: {template_path}")
        return ""
        
    try:
        doc = Document(template_path)
        full_text = "\n".join([para.text for para in doc.paragraphs])
        print(f"Шаблон '{template_name}' успешно прочитан. Длина текста: {len(full_text)} символов.")
        return full_text
    except Exception as e:
        print(f"ОШИБКА при чтении шаблона '{template_name}': {e}")
        return ""

# --- API Эндпоинты ---

@app.get("/")
def read_root():
    return {"status": "Smart Writer API is running"}

@app.post("/process")
def process_user_request(request: ProcessRequestModel):
    """
    Универсальный эндпоинт для обработки запросов на генерацию документа
    или поиск определения термина.
    """
    user_query = request.query
    request_type = request.request_type
    template_name = request.template_name
    print(f"\n--- ЗАПРОС: '{user_query}' | ТИП: {request_type} | ШАБЛОН: {template_name} ---")

    if request_type == "term":
        # --- Путь 1: Ищем определение термина с очисткой ---
        try:
            relevant_context = ks.search_relevant_knowledge(query=user_query, n_results=1)
            if not relevant_context or "не найдена" in relevant_context:
                return {"status": "error", "message": f"Определение для термина '{user_query}' не найдено."}

            term_prompt = f"""
            Ты — ассистент, который находит точные определения терминов.
            ТВОЯ ЗАДАЧА: Извлечь чистое, понятное определение для термина "{user_query}" из предоставленного текста.
            ИСХОДНЫЙ ТЕКСТ (МОЖЕТ СОДЕРЖАТЬ HTML-РАЗМЕТКУ):
            ---
            {relevant_context}
            ---
            ИНСТРУКЦИИ:
            1.  Внимательно прочитай ИСХОДНЫЙ ТЕКСТ.
            2.  Найди в нем определение для термина "{user_query}".
            3.  Сформулируй ответ, но **ОБЯЗАТЕЛЬНО УБЕРИ ВСЕ HTML-ТЕГИ**.
            4.  Ответ должен быть коротким, четким и содержать только определение.
            5.  Если в тексте нет четкого определения, напиши "Определение не найдено в предоставленном тексте."
            Приступай к работе.
            """
            clean_definition = generate_text(term_prompt)
            return {"status": "success", "result_type": "term", "term": user_query, "definition": clean_definition}
        except Exception as e:
            return {"status": "error", "message": f"Не удалось сгенерировать определение. Причина: {e}"}

    elif request_type == "document":
        # --- Путь 2: Генерируем документ по шаблону или как раньше ---
        try:
            relevant_context = ks.search_relevant_knowledge(query=user_query, n_results=15)
            
            # --- Читаем шаблон, если он указан ---
            template_content = read_template_file(template_name)
            
            if template_content:
                # Промт, если шаблон ЕСТЬ (ЖЕСТКИЙ И ПОШАГОВЫЙ)
                prompt = f"""
                ТЫ — «Ассемблер Документов». Твоя единственная и исключительная задача — взять ШАБЛОН и заполнить его информацией из БАЗЫ ЗНАНИЙ. Ты не пишешь, не создаешь и не анализируешь — ты только собираешь.

                ЗАПРЕТЫ И НЕПРЕЛОЖНЫЕ ПРАВИЛА:
                1.  СТРУКТУРА - ЭТО ЗАКОН. Ты должен использовать ТОЧНУЮ структуру, заголовки, нумерацию, таблицы и форматирование из ШАБЛОНА. Нельзя добавлять, удалять, менять порядок или объединять разделы.
                2.  ИНФОРМАЦИЯ ТОЛЬКО ИЗ БАЗЫ ЗНАНИЙ. Ты можешь использовать только информацию, предоставленную в БАЗЕ ЗНАНИЙ. Если для раздела нет информации, пиши ТОЛЬКО '[Данные из Базы Знаний отсутствуют]'.
                3.  ЗАПРЕТ НА ГАЛЛЮЦИНАЦИЮ. Под абсолютным запретом. Не придумывай данные, факты, характеристики, описания. Если нет данных в Базе Знаний - пиши, что их нет.
                4.  СОХРАНЕНИЕ ФОРМАТИРОВАНИЯ. Если в ШАБЛОНЕ есть таблица, ты должен заполнить таблицу. Если есть список - заполняй список. Сохраняй оригинальное форматирование.

                АЛГОРИТМ РАБОТЫ (ВЫПОЛНИТЬ ПОШАГОВО):

                ШАГ 1: АНАЛИЗ ЗАПРОСА
                - Пользовательский запрос: "{user_query}"
                - Определи основной объект автоматизации: "Цифровой двойник".

                ШАГ 2: АНАЛИЗ ШАБЛОНА
                - Внимательно прочитай весь текст ШАБЛОНА, который приведен ниже.
                - Определи его структуру: все заголовки, подзаголовки, таблицы, списки, нумерацию. Запомни эту структуру. Это твой каркас.

                ШАГ 3: АНАЛИЗ БАЗЫ ЗНАНИЙ
                - Внимательно прочитай всю информацию, предоставленную в БАЗЕ ЗНАНИЙ.
                - Найди все фрагменты, которые относятся к объекту "Цифровой двойник".

                ШАГ 4: СБОР ИНФОРМАЦИИ ПО РАЗДЕЛАМ
                - Для КАЖДОГО раздела и подраздела из ШАБЛОНА:
                    a. Найди в БАЗЕ ЗНАНИЙ релевантную информацию.
                    b. Если информация есть - подготовь ее для вставки, сохраняя официальный стиль.
                    c. Если информации НЕТ - подготовь к вставке фразу '[Данные из Базы Знаний отсутствуют]'.

                ШАГ 5: ГЕНЕРАЦИЯ ИТОГОВОГО ДОКУМЕНТА
                - Создай итоговый документ.
                - Начни с точного заголовка из ШАБЛОНА.
                - Последовательно, раздел за разделом, заполняй каркас (структуру из Шага 2) информацией, подготовленной на Шаге 4.
                - Если в ШАБЛОНЕ есть таблицы, заполни их, используя данные из БАЗЫ ЗНАНИЙ. Если данных для таблицы нет, оставь таблицу с пустыми ячейками или с фразой '[Данные из Базы Знаний отсутствуют]' в ячейках.
                - Для общих полей (Заказчик, Исполнитель, Дата) используй общие наименования: "Заказчик", "Исполнитель", текущую дату.

                ШАГ 6: ФИНАЛЬНАЯ ПРОВЕРКА
                - Перечитай сгенерированный документ.
                - Проверь: соответствует ли он ТОЧНОЙ структуре ШАБЛОНА?
                - Проверь: нет ли в нем придуманной информации?
                - Если есть хоть одно нарушение - вернись к Шагу 5 и исправь.

                ---
                ШАБЛОН (СТРОГО СЛЕДУЙ ЭТОЙ СТРУКТУРЕ И ФОРМАТУ):
                ---
                {template_content}
                ---

                БАЗА ЗНАНИЙ (ТОЛЬКО ЭТА ИНФОРМАЦИЯ ДОСТУПНА):
                ---
                {relevant_context}
                ---

                ПРИСТУПАЙ К ВЫПОЛНЕНИЮ АЛГОРИТМА.
                """
            else:
                # Промт, если шаблон НЕ указан (старая логика)
                intent_type, structure_prompt = classify_intent_and_structure(user_query)
                prompt = f"""
                Ты — старший технический писатель. Создай документ на основе запроса и базы знаний.
                ЗАПРОС: "{user_query}"
                БАЗА ЗНАНИЙ:
                ---
                {relevant_context}
                ---
                ИНСТРУКЦИИ: Создай структурированный документ.
                """
            
            generated_text = generate_text(prompt)
            title = f"Документ: {user_query}"
            docx_path = create_docx(content=generated_text, title=title)
            
            return {"status": "success", "result_type": "document", "file_path": docx_path}

        except Exception as e:
            return {"status": "error", "message": f"Произошла непредвиденная ошибка: {e}"}
    
    else:
        return {"status": "error", "message": f"Неверный тип запроса: '{request_type}'. Используйте 'document' или 'term'."}

# --- Старые эндпоинты для совместимости ---

@app.post("/generate")
def generate_documentation(request: RequestModel):
    """Старый эндпоинт для генерации документов. Оставлен для совместимости."""
    return process_user_request(ProcessRequestModel(query=request.query, request_type="document"))

@app.post("/get_term")
def get_term_definition(request: TermRequestModel):
    """Эндпоинт для получения определения конкретного термина."""
    return process_user_request(ProcessRequestModel(query=request.term, request_type="term"))