# services/knowledge_service.py (Версия с GPT4All, Git, Confluence и локальными файлами)
import os
import chromadb
from chromadb.config import Settings
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from typing import List

# Импортируем наши старые сервисы для загрузки данных
from services.git_service import load_git_knowledge
from services.confluence_service import search_confluence # Он нам понадобится для API

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

    def _load_local_files(self) -> str:
        """Читает все .pdf и .docx файлы из папки 'data' и возвращает единый текст."""
        data_folder = "data"
        all_texts = []
        print("Загрузка данных из локальной папки 'data'...")
        
        try:
            for filename in os.listdir(data_folder):
                file_path = os.path.join(data_folder, filename)
                print(f"  Обрабатываю файл: {filename}")

                if filename.endswith(".pdf"):
                    loader = PyPDFLoader(file_path)
                    documents = loader.load()
                    text_content = "\n\n".join([doc.page_content for doc in documents])
                    all_texts.append(text_content)

                elif filename.endswith(".docx"):
                    loader = Docx2txtLoader(file_path)
                    documents = loader.load()
                    text_content = documents[0].page_content
                    all_texts.append(text_content)
                
                elif filename.endswith(".doc"):
                    print(f"    ПРОПУЩЕН (старый формат .doc): {filename}. Пожалуйста, преобразуйте в .docx.")
                
                else:
                    print(f"    Пропускаю файл неподдерживаемого формата: {filename}")

        except FileNotFoundError:
            print(f"    Папка '{data_folder}' не найдена. Локальные файлы не будут добавлены.")
            return ""
        except Exception as e:
            print(f"    Произошла ошибка при чтении файлов: {e}")
            return ""

        if not all_texts:
            print("    В папке 'data' не найдено поддерживаемых документов (.pdf, .docx).")
            return ""
        
        local_text = "\n\n--- НОВЫЙ ЛОКАЛЬНЫЙ ДОКУМЕНТ ---\n\n".join(all_texts)
        print(f"    Загружено текста из локальных файлов: {len(local_text)} символов.")
        return local_text

    def _load_all_confluence_data(self) -> str:
        """Скачивает ВСЕ страницы из указанного пространства Confluence."""
        print("Начинаю загрузку ВСЕХ данных из Confluence...")
        space_key = os.getenv("SPACE_KEY")
        
        if not space_key:
            print("    ОШИБКА: Переменная SPACE_KEY не найдена в .env файле. Пропускаю загрузку из Confluence.")
            return ""

        # Здесь мы используем функцию из confluence_service.py для получения всех страниц
        # Вам может понадобиться добавить эту функцию в confluence_service.py
        # или адаптировать этот код под ваш API-клиент
        try:
            # Предполагается, что в confluence_service.py есть такая функция
            from services.confluence_service import get_all_pages_from_space
            pages_content = get_all_pages_from_space(space_key=space_key)
            
            if not pages_content:
                print("    В Confluence не найдено страниц или произошла ошибка.")
                return ""

            full_confluence_text = "\n\n--- НОВАЯ СТРАНИЦА CONFLUENCE ---\n\n".join(pages_content)
            print(f"    Загружено текста из Confluence: {len(full_confluence_text)} символов.")
            return full_confluence_text
            
        except ImportError:
            print("    ОШИБКА: Функция get_all_pages_from_space не найдена в confluence_service.py. Пропускаю загрузку.")
            print("    Вам нужно добавить эту функцию для скачивания всех страниц.")
            return ""
        except Exception as e:
            print(f"    Произошла ошибка при загрузке из Confluence: {e}")
            return ""

    def create_knowledge_base(self):
        """Индексирует все знания из Git, Confluence и локальных файлов в векторную базу."""
        print("Начинаю индексацию базы знаний из всех источников...")
        
        # 1. Загружаем данные из всех источников
        print("Загрузка данных из Git...")
        git_text = load_git_knowledge()

        # Вызываем НОВУЮ функцию для загрузки всех данных из Confluence
        confluence_text = self._load_all_confluence_data()

        # Вызываем функцию для загрузки локальных файлов
        local_text = self._load_local_files()
        
        # 2. Объединяем все тексты в один
        full_text = (
            f"--- ИНФОРМАЦИЯ ИЗ GIT ---\n{git_text}\n\n"
            f"--- ИНФОРМАЦИЯ ИЗ CONFLUENCE ---\n{confluence_text}\n\n"
            f"--- ИНФОРМАЦИЯ ИЗ ЛОКАЛЬНЫХ ФАЙЛОВ ---\n{local_text}"
        )
        
        # 3. Разбиваем на чанки
        chunks = self._chunk_text(full_text)
        print(f"Текст разбит на {len(chunks)} чанков.")
        
        # 4. Очищаем старую коллекцию
        self.client.delete_collection(name="asupgr_knowledge")
        self.collection = self.client.get_or_create_collection(name="asupgr_knowledge")
        
        # 5. Создаем эмбеддинги для всех чанков
        print("Создаю эмбеддинги для чанков... Это может занять время.")
        embeddings = self.embedding_model.embed_documents(chunks)
        
        # 6. Добавляем в базу
        ids = [str(i) for i in range(len(chunks))]
        self.collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids
        )
        print(f"База знаний успешно проиндексирована. Добавлено {len(chunks)} документов.")

    def search_relevant_knowledge(self, query: str, n_results: int = 80) -> str:
        """Ищет релевантные чанки по запросу пользователя."""
        print(f"Ищу релевантную информацию по запросу: '{query}'")
        
        query_embedding = self.embedding_model.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "Релевантная информация в базе знаний не найдена."
            
        retrieved_chunks = results['documents'][0]
        context = "\n\n---\n\n".join(retrieved_chunks)
        print(f"Найдено {len(retrieved_chunks)} релевантных чанков.")
        
        return context