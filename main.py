"""Smart Writer API - Main application file."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from dotenv import load_dotenv

from services.knowledge_service import KnowledgeService
from app.routes import document_routes, feedback_routes, viewer_routes

load_dotenv()

# --- Инициализация ---
app = FastAPI(title="Smart Writer API")

# Разрешаем обращения из браузера (в том числе при открытии viewer.html локально или с другого origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализируем KnowledgeService с обработкой ошибок
try:
    ks = KnowledgeService()
except Exception as e:
    print(f"ОШИБКА при инициализации KnowledgeService: {e}")
    print("Попытка пересоздать базу знаний...")
    if os.path.exists("./chroma_db"):
        try:
            shutil.rmtree("./chroma_db")
            print("Старая база данных удалена.")
        except Exception as rm_error:
            print(f"Ошибка при удалении базы: {rm_error}")
    ks = KnowledgeService()

# Устанавливаем KnowledgeService в роуты
document_routes.set_knowledge_service(ks)

# Подключаем роуты
app.include_router(document_routes.router)
app.include_router(feedback_routes.router)
app.include_router(viewer_routes.router)


@app.get("/")
def read_root():
    """Root endpoint."""
    return {"status": "Smart Writer API is running"}
