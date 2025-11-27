"""Routes for document generation."""
from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

from app.models.requests import ProcessRequestModel, RequestModel, TermRequestModel
from app.utils.document_utils import (
    classify_intent_and_structure,
    is_question_like,
    has_strong_doc_type_markers,
    get_tz_sections,
    get_manual_sections,
)
from app.utils.prompts import (
    build_term_prompt,
    build_qa_prompt,
    build_tz_section_prompt,
    build_manual_section_prompt,
    build_general_document_prompt,
)
from services.openai_service import generate_text, LLMError
from services.knowledge_service import KnowledgeService
from services.docx_service import create_docx
from services.git_service import search_images_by_keywords
import re

router = APIRouter()

# Глобальный экземпляр KnowledgeService (инициализируется в main.py)
ks: KnowledgeService | None = None


def set_knowledge_service(service: KnowledgeService):
    """Устанавливает экземпляр KnowledgeService для использования в роутах."""
    global ks
    ks = service


@router.post("/process")
def process_user_request(request: ProcessRequestModel):
    """
    Универсальный эндпоинт для обработки запросов на генерацию документа
    или поиск определения термина.
    """
    if ks is None:
        return {"status": "error", "message": "KnowledgeService не инициализирован"}
    
    user_query = request.query
    request_type = request.request_type
    template_name = request.template_name
    print(f"\n--- ЗАПРОС: '{user_query}' | ТИП: {request_type} | ШАБЛОН: {template_name} ---")

    # Определяем систему из запроса
    detected_system = ks.detect_system_from_query(user_query) if ks else None
    
    if request_type == "term":
        # --- Путь 1: Ищем определение термина с очисткой ---
        try:
            relevant_context = ks.search_relevant_knowledge(query=user_query, n_results=1, system=detected_system)
            if not relevant_context or "не найдена" in relevant_context:
                return {"status": "error", "message": f"Определение для термина '{user_query}' не найдено."}

            term_prompt = build_term_prompt(user_query, relevant_context)
            clean_definition = generate_text(term_prompt)
            return {"status": "success", "result_type": "term", "term": user_query, "definition": clean_definition}
        except Exception as e:
            return {"status": "error", "message": f"Не удалось сгенерировать определение. Причина: {e}"}

    elif request_type == "document":
        # --- Путь 2: Генерируем документ по шаблону или как раньше ---
        try:
            if is_question_like(user_query) and not has_strong_doc_type_markers(user_query):
                relevant_context = ks.search_relevant_knowledge(query=user_query, n_results=40, system=detected_system)
                qa_prompt = build_qa_prompt(user_query, relevant_context)
                qa_answer = generate_text(qa_prompt)
                
                # Ищем изображения по ключевым словам из запроса
                keywords = _extract_keywords_from_query(user_query)
                images = search_images_by_keywords(keywords, system=detected_system) if keywords else []
                
                return {
                    "status": "success",
                    "result_type": "qa",
                    "answer": qa_answer,
                    "images": images,
                    "system": detected_system
                }

            intent_type, structure_prompt = classify_intent_and_structure(user_query)

            if intent_type == "tz":
                sections = get_tz_sections()
                section_texts = []

                for section_title, section_hint in sections:
                    section_query = f"{user_query}. Раздел ТЗ: {section_title}. {section_hint}"
                    section_context = ks.search_relevant_knowledge(query=section_query, n_results=60, system=detected_system)
                    section_prompt = build_tz_section_prompt(user_query, section_title, section_hint, section_context)
                    section_result = generate_text(section_prompt)
                    section_texts.append(section_result.strip())

                generated_text = "\n\n".join(section_texts)
            elif intent_type == "manual":
                sections = get_manual_sections()
                section_texts = []

                for section_title, section_hint in sections:
                    section_query = f"{user_query}. Раздел Руководства пользователя: {section_title}. {section_hint}"
                    section_context = ks.search_relevant_knowledge(query=section_query, n_results=60, system=detected_system)
                    section_prompt = build_manual_section_prompt(user_query, section_title, section_hint, section_context)
                    section_result = generate_text(section_prompt)
                    section_texts.append(section_result.strip())

                generated_text = "\n\n".join(section_texts)
            else:
                relevant_context = ks.search_relevant_knowledge(query=user_query, n_results=100, system=detected_system)
                prompt = build_general_document_prompt(user_query, relevant_context)
                generated_text = generate_text(prompt)
            
            # Ищем изображения по ключевым словам из запроса
            keywords = _extract_keywords_from_query(user_query)
            images = search_images_by_keywords(keywords, system=detected_system) if keywords else []

            title = f"Документ: {user_query}"
            docx_path = create_docx(content=generated_text, title=title)
            
            return {
                "status": "success",
                "result_type": "document",
                "file_path": docx_path,
                "content": generated_text,
                "images": images,
                "system": detected_system
            }

        except Exception as e:
            return {"status": "error", "message": f"Произошла непредвиденная ошибка: {e}"}
    
    else:
        return {"status": "error", "message": f"Неверный тип запроса: '{request_type}'. Используйте 'document' или 'term'."}


@router.post("/generate")
def generate_documentation(request: RequestModel):
    """Старый эндпоинт для генерации документов. Оставлен для совместимости."""
    return process_user_request(ProcessRequestModel(query=request.query, request_type="document"))


@router.post("/get_term")
def get_term_definition(request: TermRequestModel):
    """Эндпоинт для получения определения конкретного термина."""
    return process_user_request(ProcessRequestModel(query=request.term, request_type="term"))


@router.get("/download/{filename:path}")
def download_file(filename: str):
    """Скачивание сгенерированных документов из папки output."""
    # Убираем путь к папке output, если он есть в filename
    if filename.startswith("output/"):
        filename = filename[7:]  # Убираем "output/"
    elif filename.startswith("output\\"):
        filename = filename[7:]  # Убираем "output\"
    
    file_path = os.path.join("output", filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        # Проверяем, что файл находится в папке output (безопасность)
        abs_file_path = os.path.abspath(file_path)
        abs_output_dir = os.path.abspath("output")
        if abs_file_path.startswith(abs_output_dir):
            return FileResponse(
                path=file_path,
                filename=os.path.basename(filename),  # Только имя файла для скачивания
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
    return {"status": "error", "message": "Файл не найден"}


def _extract_keywords_from_query(query: str) -> list:
    """
    Извлекает ключевые слова из запроса для поиска изображений.
    Удаляет стоп-слова и возвращает значимые слова.
    """
    # Стоп-слова на русском
    stop_words = {
        "как", "что", "где", "когда", "кто", "зачем", "почему", "какие", "какая", "какой",
        "в", "на", "с", "по", "для", "от", "до", "из", "к", "о", "об", "про", "со", "под",
        "и", "или", "а", "но", "да", "нет", "не", "ни", "же", "ли", "бы", "б", "то", "это",
        "есть", "быть", "был", "была", "было", "были", "стать", "стал", "стала", "стало",
        "создать", "создай", "создание", "сделать", "сделай", "добавить", "добавь",
        "техническое", "задание", "руководство", "пользователя", "инструкция"
    }
    
    # Убираем знаки препинания и приводим к нижнему регистру
    words = re.findall(r'\b[а-яё]+\b', query.lower())
    
    # Фильтруем стоп-слова и короткие слова (меньше 3 символов)
    keywords = [w for w in words if w not in stop_words and len(w) >= 3]
    
    # Ограничиваем количество ключевых слов (берем самые длинные)
    keywords = sorted(set(keywords), key=len, reverse=True)[:5]
    
    return keywords


