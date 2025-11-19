# main.py (ВЕРСИЯ С ЖЕСТКИМ ПОШАГОВЫМ ПРОМТОМ ДЛЯ ШАБЛОНОВ)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from datetime import datetime
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

# Разрешаем обращения из браузера (в том числе при открытии viwer.html локально или с другого origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ks = KnowledgeService()

# --- Pydantic Модели для запросов ---

class RequestModel(BaseModel):
    query: str

class TermRequestModel(BaseModel):
    term: str

class ProcessRequestModel(BaseModel):
    query: str
    request_type: str  # "document" или "term"
    template_name: str | None = None  # Имя файла шаблона, например "ГОСТ34_Техническое задание.doc"

class FeedbackRequestModel(BaseModel):
    author: str | None = None
    doc_type: str | None = None
    doc_ref: str | None = None
    operation: str | None = None  # "delete", "replace", "add", "comment"
    old_text: str | None = None
    new_text: str | None = None
    comment: str | None = None

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

def get_tz_sections() -> list[tuple[str, str]]:
    sections = [
        ("1. Общие положения", "описать общие положения, контекст, обозначения, сокращения, плановые сроки и порядок оформления и предъявления результатов работ"),
        ("2. Назначение и цели создания Системы", "описать назначение системы, цели создания, ожидаемые эффекты, измеримые показатели и задачи"),
        ("3. Характеристика объектов автоматизации", "описать профиль организации-заказчика, объекты автоматизации, материальные и информационные объекты"),
        ("4. Требования к Системе", "описать функциональные, нефункциональные, эксплуатационные, надежности, к интерфейсам, интеграциям и безопасности"),
        ("5. Состав и содержание работ по созданию Системы", "описать этапы и виды работ, что выполняется на каждом этапе жизненного цикла"),
        ("6. Порядок контроля и приемки Системы", "описать виды и этапы испытаний, критерии приемки, порядок оформления результатов"),
        ("7. Требования к подготовке объекта автоматизации к вводу Системы в действие", "описать действия и ответственность заказчика, какие условия должны быть выполнены к вводу системы"),
        ("8. Требования к документированию", "описать состав комплектов документации, виды документов и общие требования к ним"),
        ("9. Источники разработки", "описать перечень нормативных документов, исходных материалов и проектной документации, на основании которых ведется разработка"),
        ("10. Приложения", "описать, какие материалы и таблицы могут быть вынесены в приложения к ТЗ"),
    ]
    return sections

def get_manual_sections() -> list[tuple[str, str]]:
    sections = [
        ("1. Введение", "кратко описать назначение системы для пользователя, целевую аудиторию руководства и общую структуру документа"),
        ("2. Назначение и область применения", "описать, для каких задач и в каких сценариях конечный пользователь использует систему"),
        ("3. Требования к рабочему месту и окружению", "описать минимальные требования к оборудованию, ПО, сетевой инфраструктуре, правам доступа"),
        ("4. Установка и запуск системы", "описать шаги по установке, первичной настройке и запуску клиентских компонентов/веб-интерфейса"),
        ("5. Обзор интерфейса и основных экранов", "описать основные разделы интерфейса, навигацию, ключевые элементы экранов"),
        ("6. Роли пользователей и их права", "описать типы пользователей (оператор, инженер, администратор и т.п.) и доступные им функции"),
        ("7. Типовые сценарии работы", "пошагово описать основные пользовательские сценарии: подготовка данных, запуск расчетов/моделирования, анализ результатов"),
        ("8. Работа с отчетами и результатами моделирования", "описать просмотр, экспорт и интерпретацию отчетов и визуализаций"),
        ("9. Обработка ошибок и нестандартных ситуаций", "описать типовые сообщения об ошибках, их причины и рекомендуемые действия пользователя"),
        ("10. Резервное копирование и восстановление пользовательских данных", "описать, что пользователь может/должен делать для сохранения и восстановления своих данных (если применимо)"),
        ("11. Приложения", "описать, какие дополнительные материалы, таблицы и словари терминов могут быть вынесены в приложения к руководству"),
    ]
    return sections

def is_question_like(query: str) -> bool:
    q = query.strip().lower()
    if "?" in q:
        return True

    question_words = {
        "как",
        "что",
        "кто",
        "где",
        "когда",
        "зачем",
        "почему",
        "какие",
        "какая",
        "какой",
        "каково",
        "сколько",
    }

    tokens = q.split()
    if not tokens:
        return False

    # Прямой вопрос: начинается с вопросительного слова
    if tokens[0] in question_words:
        return True

    # Вариант вроде "Документ: Какие специалисты ..." или "Вопрос: Как ..."
    first = tokens[0].rstrip(":")
    if first in {"документ", "вопрос", "запрос"} and len(tokens) > 1 and tokens[1] in question_words:
        return True

    return False

def has_strong_doc_type_markers(query: str) -> bool:
    q = query.lower()
    markers = (
        "техническое задание",
        "тз",
        "руководство пользователя",
        "инструкция",
    )
    return any(m in q for m in markers)

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

@app.post("/feedback")
def submit_feedback(request: FeedbackRequestModel):
    """Принимает правку к документации и сохраняет её в локальный markdown-файл."""
    try:
        os.makedirs("feedback", exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        author = (request.author or "unknown").replace("@", "").replace(" ", "_")
        filename = f"{timestamp}_{author}_feedback.md"
        file_path = os.path.join("feedback", filename)

        content_lines = [
            "# Правка документации",
            "",
            f"- Автор: {request.author or '-'}",
            f"- Тип документа: {request.doc_type or '-'}",
            f"- Документ/раздел: {request.doc_ref or '-'}",
            f"- Операция: {request.operation or '-'}",
            "",
            "## Было",
            (request.old_text or "-"),
            "",
            "## Стало",
            (request.new_text or "-"),
            "",
            "## Комментарий",
            (request.comment or "-"),
            "",
        ]

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines))

        print(f"Правка сохранена в файл: {file_path}")
        return {"status": "success", "file_path": file_path}

    except Exception as e:
        return {"status": "error", "message": f"Не удалось сохранить правку: {e}"}

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
            if is_question_like(user_query) and not has_strong_doc_type_markers(user_query):
                relevant_context = ks.search_relevant_knowledge(query=user_query, n_results=40)

                qa_prompt = f"""
                Ты — эксперт по системе и ассистент по технической документации.

                ТВОЯ ЗАДАЧА: ответить на ВОПРОС пользователя по существу, используя только предоставленную БАЗУ ЗНАНИЙ.

                ВОПРОС ПОЛЬЗОВАТЕЛЯ:
                "{user_query}"

                БАЗА ЗНАНИЙ:
                ---
                {relevant_context}
                ---

                ИНСТРУКЦИИ:
                1. Ответь ТОЛЬКО на этот вопрос. Не нужно составлять отдельный документ, ТЗ или Руководство пользователя.
                2. НЕ добавляй заголовки вида "Руководство пользователя", "Техническое задание", "Документ" и т.п.
                3. Используй БАЗУ ЗНАНИЙ, не придумывай факты. Если информации явно не хватает, аккуратно укажи, какие данные нужно уточнить.
                4. Если вопрос про действия пользователя ("как сделать ..."), опиши шаги по порядку с точки зрения пользователя системы.
                5. Объём ответа: от 1 до 5 абзацев, можно использовать маркированные списки для шагов или перечней.
                6. Не смешивай описания разных систем: если в БАЗЕ ЗНАНИЙ несколько систем, ориентируйся на ту, которая прямо следует из вопроса.
                """

                qa_answer = generate_text(qa_prompt)
                return {"status": "success", "result_type": "qa", "answer": qa_answer}

            intent_type, structure_prompt = classify_intent_and_structure(user_query)

            if intent_type == "tz":
                sections = get_tz_sections()
                section_texts = []

                for section_title, section_hint in sections:
                    section_query = f"{user_query}. Раздел ТЗ: {section_title}. {section_hint}"
                    section_context = ks.search_relevant_knowledge(query=section_query, n_results=60)

                    section_prompt = f"""
                    Ты — старший технический писатель и системный аналитик.

                    ТВОЯ ЗАДАЧА: на основе ЗАПРОСА, БАЗЫ ЗНАНИЙ и описания раздела подготовить ПОЛНЫЙ текст раздела Технического задания под названием "{section_title}".

                    ЗАПРОС ПОЛЬЗОВАТЕЛЯ:
                    "{user_query}"

                    РАЗДЕЛ ТЗ:
                    "{section_title}"

                    ЧТО НУЖНО ОСВЕТИТЬ В ЭТОМ РАЗДЕЛЕ:
                    {section_hint}

                    БАЗА ЗНАНИЙ:
                    ---
                    {section_context}
                    ---

                    ПРАВИЛА:
                    1. СГЕНЕРИРУЙ ТОЛЬКО ТЕКСТ РАЗДЕЛА "{section_title}", со всеми его подпунктами, но без других разделов.
                    2. НЕ ДЕЛАЙ КРАТКОЕ РЕЗЮМЕ. Пиши развернуто, максимально подробно, опираясь на БАЗУ ЗНАНИЙ.
                    3. НЕ ПРИДУМЫВАЙ ФАКТЫ ВНЕ БАЗЫ ЗНАНИЙ. Если информации не хватает, явно пиши, какие данные нужно уточнить.
                    4. НЕ СМЕШИВАЙ ОПИСАНИЯ РАЗНЫХ СИСТЕМ. Если в БАЗЕ ЗНАНИЙ есть разные системы, выбирай только ту, которая соответствует запросу.
                    5. СОХРАНЯЙ ОФИЦИАЛЬНО-ДЕЛОВОЙ СТИЛЬ И СТРУКТУРУ ГОСТОВОГО ТЗ.
                    """
                    section_result = generate_text(section_prompt)
                    section_texts.append(section_result.strip())

                generated_text = "\n\n".join(section_texts)
            elif intent_type == "manual":
                sections = get_manual_sections()
                section_texts = []

                for section_title, section_hint in sections:
                    section_query = f"{user_query}. Раздел Руководства пользователя: {section_title}. {section_hint}"
                    section_context = ks.search_relevant_knowledge(query=section_query, n_results=60)

                    section_prompt = f"""
                    Ты — технический писатель, создающий подробное Руководство пользователя по системе.

                    ТВОЯ ЗАДАЧА: на основе ЗАПРОСА, БАЗЫ ЗНАНИЙ и описания раздела подготовить ПОЛНЫЙ текст раздела Руководства пользователя под названием "{section_title}".

                    ЗАПРОС ПОЛЬЗОВАТЕЛЯ:
                    "{user_query}"

                    РАЗДЕЛ РУКОВОДСТВА:
                    "{section_title}"

                    ЧТО НУЖНО ОСВЕТИТЬ В ЭТОМ РАЗДЕЛЕ:
                    {section_hint}

                    БАЗА ЗНАНИЙ:
                    ---
                    {section_context}
                    ---

                    ПРАВИЛА:
                    1. СГЕНЕРИРУЙ ТОЛЬКО ТЕКСТ РАЗДЕЛА "{section_title}", со всеми его подпунктами, но без других разделов.
                    2. ПИШИ С ТОЧКИ ЗРЕНИЯ КОНЕЧНОГО ПОЛЬЗОВАТЕЛЯ/ОПЕРАТОРА: что он видит в интерфейсе и какие шаги выполняет.
                    3. НЕ ПЕРЕПИСЫВАЙ ТЕХНИЧЕСКОЕ ЗАДАНИЕ. Описывай именно практическое использование системы, а не цели проекта и бизнес-контекст.
                    4. МАКСИМАЛЬНО ИСПОЛЬЗУЙ БАЗУ ЗНАНИЙ. Если в ней мало данных по интерфейсу, переходи на аккуратные обобщения и явно помечай, что описываешь типовой сценарий.
                    5. НЕ ПРИДУМЫВАЙ НОВЫЕ СУЩЕСТВА, ПОДСИСТЕМЫ И ТЕРМИНЫ, КОТОРЫХ НЕТ В БАЗЕ ЗНАНИЙ.
                    6. ИЗБЕГАЙ ПУСТОЙ ОБЩЕЙ ТЕОРИИ. Каждый подраздел должен помогать пользователю реально работать с системой.
                    """
                    section_result = generate_text(section_prompt)
                    section_texts.append(section_result.strip())

                generated_text = "\n\n".join(section_texts)
            else:
                relevant_context = ks.search_relevant_knowledge(query=user_query, n_results=100)

                prompt = f"""
                Ты — старший технический писатель и системный аналитик.

                ТВОЯ ЗАДАЧА: на основе ЗАПРОСА и БАЗЫ ЗНАНИЙ подготовить МАКСИМАЛЬНО ПОДРОБНЫЙ, полноформатный документ (например, Техническое задание по ГОСТ, подробное Руководство пользователя или аналогичный по глубине документ), а не краткую выжимку.

                ЗАПРОС:
                "{user_query}"

                БАЗА ЗНАНИЙ:
                ---
                {relevant_context}
                ---

                ОБЩИЕ ПРАВИЛА:
                1.  НЕ ДЕЛАЙ КРАТКОЕ РЕЗЮМЕ. Это должен быть развернутый документ уровня аналитика/проектировщика, а не конспект.
                2.  ИСПОЛЬЗУЙ МАКСИМУМ РЕЛЕВАНТНОЙ ИНФОРМАЦИИ из БАЗЫ ЗНАНИЙ, не выбрасывай важные детали, если они относятся к теме.
                3.  НЕ ПРИДУМЫВАЙ ФАКТЫ. Используй только то, что есть в БАЗЕ ЗНАНИЙ. Если данных для какого‑то аспекта нет — прямо укажи, что информация отсутствует.
                4.  НЕЛЬЗЯ СМЕШИВАТЬ РАЗНЫЕ СИСТЕМЫ. Если в БАЗЕ ЗНАНИЙ есть описания разных систем (АСУ ПГР, цифровой двойник, другие), выбери ОДНУ целевую систему/объект, который следует из ЗАПРОСА, и описывай только её. Не объединяй описания разных систем в один документ.
                5.  СТРУКТУРА ДОЛЖНА БЫТЬ ЛОГИЧЕСКИ ПОЛНОЙ: введение, область применения, термины и сокращения (если есть), общие сведения о системе, требования (функциональные, нефункциональные, к интерфейсам, интеграциям, надёжности и т.п.), архитектура/состав, пользовательские роли и сценарии, порядок ввода в действие, сопровождение и т.д. Адаптируй структуру под тип документа, но делай её максимально полной.

                ИНСТРУКЦИИ ПО РАБОТЕ:
                1.  Определи тип документа по ЗАПРОСУ (Техническое задание, Руководство пользователя, описание подсистемы и т.п.).
                2.  Определи целевую систему/объект (например, цифровой двойник, АСУ ПГР и т.п.) и строго придерживайся именно её.
                3.  Внимательно изучи БАЗУ ЗНАНИЙ и выбери все фрагменты, относящиеся к выбранному типу документа и целевой системе.
                4.  Построй подробный документ с чёткими разделами и подпунктами. Каждый раздел заполняй максимально полно, используя релевантные фрагменты из БАЗЫ ЗНАНИЙ.
                5.  Если для какого‑то раздела данных мало или нет, явно укажи это текстом (например: "Информация по данному аспекту в базе знаний отсутствует"), но не опускай раздел полностью.

                СФОРМИРУЙ ИТОГОВЫЙ ДОКУМЕНТ:
                - Полноформатный, детализированный.
                - В официально‑деловом стиле, понятный аналитику, архитектору и разработчику.
                - Без искусственного сокращения объёма: не пытайся уместить всё в несколько абзацев, раскрывай тему настолько подробно, насколько позволяет БАЗА ЗНАНИЙ.
                """

                generated_text = generate_text(prompt)

            title = f"Документ: {user_query}"
            docx_path = create_docx(content=generated_text, title=title)
            
            return {
                "status": "success",
                "result_type": "document",
                "file_path": docx_path,
                "content": generated_text,
            }

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