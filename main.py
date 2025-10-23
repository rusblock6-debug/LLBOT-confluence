# main.py
from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from services.git_service import load_git_knowledge
from services.confluence_service import search_confluence
from services.ollama_service import generate_text
from services.docx_service import create_docx

load_dotenv()

app = FastAPI(title="Smart Writer API")

class RequestModel(BaseModel):
    query: str

@app.get("/")
def read_root():
    return {"status": "Smart Writer API is running"}

@app.post("/generate")
def generate_documentation(request: RequestModel):
    user_query = request.query
    print(f"\n--- НОВЫЙ ЗАПРОС: {user_query} ---")
    
    git_context = load_git_knowledge()
    confluence_context = search_confluence(query=user_query)
    
    prompt = f"""
    Ты — опытный технический писатель. Составь документ на основе запроса и контекста.
    
    Запрос: "{user_query}"
    
    Контекст из Git:
    ---
    {git_context[:8000]}
    ---
    
    Контекст из Confluence:
    ---
    {confluence_context[:7000]}
    ---
    
    На основе ВСЕЙ информации составь четкий, структурированный документ. Используй markdown.
    """
    
    generated_text = generate_text(prompt=prompt, model="llama3.1:8b")
    docx_path = create_docx(content=generated_text, title=f"Документ по запросу: {user_query}")
    
    return {"status": "success", "file_path": docx_path}