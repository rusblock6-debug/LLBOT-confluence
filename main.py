# main.py (ФИНАЛЬНАЯ ВЕРСИЯ - должна работать без изменений)
from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from services.openai_service import generate_text 
from services.git_service import load_git_knowledge
from services.confluence_service import search_confluence
from services.docx_service import create_docx

load_dotenv()

app = FastAPI(title="Smart Writer API", version="1.0")

class RequestModel(BaseModel):
    query: str

def classify_intent(query: str) -> tuple[str, str]:
    query_lower = query.lower()
    if any(keyword in query_lower for keyword in ["техническое задание", "тех задание", "тз"]):
        return ("tz", query)
    if any(keyword in query_lower for keyword in ["руководство пользователя", "инструкция", "как пользоваться"]):
        return ("manual", query)
    if any(keyword in query_lower for keyword in ["опиши систему", "общее описание", "обзор"]):
        return ("description", query)
    if "что такое" in query_lower or "определи" in query_lower:
        term = query_lower.split("что такое")[-1].strip() or query_lower.split("определи")[-1].strip()
        return ("definition", term)
    if "пункт" in query_lower or "раздел" in query_lower:
        subject = query_lower.split("пункт")[-1].strip() or query_lower.split("раздел")[-1].strip()
        return ("section", subject)
    return ("general", query)

@app.get("/")
def read_root():
    return {"status": "Smart Writer API is running"}

@app.post("/generate")
def generate_documentation(request: RequestModel):
    user_query = request.query
    print(f"\n--- НОВЫЙ ЗАПРОС: {user_query} ---")
    
    git_context = load_git_knowledge()
    confluence_context = search_confluence(query=user_query)
    
    intent_type, subject = classify_intent(user_query)
    print(f"Определен тип запроса: {intent_type}, тема: {subject}")

    if intent_type == "tz":
        prompt = f"Ты — технический писатель. Создай структурированное Техническое Задание (ТЗ) для системы 'АСУ ПГР' на основе предоставленной документации. Включи разделы: Общие положения, Функциональные требования, Архитектура, Глоссарий. Используй только информацию из контекста. Контекст: --- {git_context[:15000]} ---"
        title = "ТЗ на систему АСУ ПГР"
    elif intent_type == "manual":
        prompt = f"Ты — технический писатель. Напиши Руководство пользователя для системы 'АСУ ПГР'. Опиши основные сценарии использования: как оператор выполняет сменное задание, как диспетчер отслеживает работу. Сделай текст понятным для конечного пользователя, с примерами. Контекст: --- {git_context[:15000]} ---"
        title = "Руководство пользователя АСУ ПГР"
    elif intent_type == "description":
        prompt = f"Ты — бизнес-аналитик. Напиши обзорное описание системы 'АСУ ПГР' для руководителя. Расскажи, какие проблемы решает система, какие у нее ключевые возможности и какую пользу она приносит. Изложи текст просто и ясно, без глубоких технических деталей. Контекст: --- {git_context[:15000]} ---"
        title = "Описание системы АСУ ПГР"
    else:
        if intent_type == "definition":
            prompt = f"На основе контекста, дай точное определение термину '{subject}'. Если определения нет, напиши 'Определение не найдено'. Контекст: --- {git_context[:10000]} ---"
        elif intent_type == "section":
            prompt = f"На основе контекста, найди и суммируй информацию по разделу/пункту '{subject}'. Если информации нет, напиши 'Информация не найдена'. Контекст: --- {git_context[:10000]} ---"
        else:
            prompt = f"Ответь на вопрос '{user_query}' по системе 'АСУ ПГР', используя только контекст. Если ответа нет, напиши 'Ответ в базе знаний отсутствует'. Контекст: --- {git_context[:10000]} ---"
        title = f"Ответ на запрос: {user_query}"

    generated_text = generate_text(prompt)
    docx_path = create_docx(content=generated_text, title=title)
    
    return {"status": "success", "file_path": docx_path}