# services/knowledge_service.py (Версия с GPT4All и ИСПРАВЛЕННЫМ ИМПОРТОМ)
import os
import chromadb
from chromadb.config import Settings
from langchain_community.embeddings import GPT4AllEmbeddings  # <-- ИСПРАВЛЕННАЯ СТРОКА
from typing import List

# Импортируем наши старые сервисы для загрузки данных
from services.git_service import load_git_knowledge
from services.confluence_service import search_confluence

class KnowledgeService:
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Инициализирует ChromaDB и модель GPT4All."""
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name="asupgr_knowledge")
        
        # Инициализируем модель GPT4All. Она скачает модель при первом запуске.
        print("Инициализирую модель GPT4All для эмбеддингов...")
        self.embedding_model = GPT4AllEmbeddings()
        print("Модель GPT4All готова к работе.")

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Разбивает большой текст на пересекающиеся чанки."""
        if not text or len(text) <= chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        return chunks

    def create_knowledge_base(self):
        """Индексирует все знания из Git и Confluence в векторную базу."""
        print("Начинаю индексацию базы знаний...")
        
        # 1. Загружаем все данные из источников
        print("Загрузка данных из Git...")
        git_text = load_git_knowledge()
        
        print("Загрузка данных из Confluence...")
        confluence_text = search_confluence(query="АСУ ПГР OR Рудопоток OR Бурение OR Планирование", limit=20)
        
        full_text = f"--- ИНФОРМАЦИЯ ИЗ GIT ---\n{git_text}\n\n--- ИНФОРМАЦИЯ ИЗ CONFLUENCE ---\n{confluence_text}"
        
        # 2. Разбиваем на чанки
        chunks = self._chunk_text(full_text)
        print(f"Текст разбит на {len(chunks)} чанков.")
        
        # 3. Очищаем старую коллекцию
        self.client.delete_collection(name="asupgr_knowledge")
        self.collection = self.client.get_or_create_collection(name="asupgr_knowledge")
        
        # 4. Создаем эмбеддинги для всех чанков (используем новый метод)
        print("Создаю эмбеддинги для чанков... Это может занять время.")
        embeddings = self.embedding_model.embed_documents(chunks)
        
        # 5. Добавляем в базу
        ids = [str(i) for i in range(len(chunks))]
        self.collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids
        )
        print(f"База знаний успешно проиндексирована. Добавлено {len(chunks)} документов.")

    def search_relevant_knowledge(self, query: str, n_results: int = 5) -> str:
        """Ищет релевантные чанки по запросу пользователя."""
        print(f"Ищу релевантную информацию по запросу: '{query}'")
        
        # 1. Создаем эмбеддинг для запроса (используем новый метод)
        query_embedding = self.embedding_model.embed_query(query)
        
        # 2. Ищем в базе
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "Релевантная информация в базе знаний не найдена."
            
        retrieved_chunks = results['documents'][0]
        
        # 3. Собираем найденные чанки в один текст
        context = "\n\n---\n\n".join(retrieved_chunks)
        print(f"Найдено {len(retrieved_chunks)} релевантных чанков.")
        
        return context