# services/knowledge_service.py (Версия с GPT4All, Git, Confluence и локальными файлами)
import os
import numpy as np
from typing import List

# Shim для совместимости chromadb с NumPy 2.x
# В NumPy 2.0 удалили np.float_ и ряд псевдонимов, которые всё ещё используют зависимости chromadb.
if not hasattr(np, "float_"):
    np.float_ = np.float64  # type: ignore[attr-defined]
if not hasattr(np, "int_"):
    np.int_ = np.int64  # type: ignore[attr-defined]
if not hasattr(np, "uint"):
    np.uint = np.uint64  # type: ignore[attr-defined]

import chromadb
from chromadb.config import Settings
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader

# Импортируем наши старые сервисы для загрузки данных
from services.git_service import load_git_knowledge
from services.confluence_service import search_confluence # Он нам понадобится для API

class KnowledgeService:
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Инициализирует ChromaDB и модель GPT4All для двух систем."""
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Создаем отдельные коллекции для каждой системы
        self.collections = {}
        systems = ["asupgr", "digital_twin"]
        
        for system in systems:
            collection_name = f"{system}_knowledge"
            try:
                self.collections[system] = self.client.get_or_create_collection(name=collection_name)
                print(f"Коллекция '{collection_name}' готова к работе.")
            except Exception as e:
                # Если ошибка связана с несовместимостью схемы БД, удаляем старую базу
                if "no such column" in str(e) or "OperationalError" in str(type(e).__name__):
                    print(f"Обнаружена несовместимость схемы базы данных ChromaDB: {e}")
                    print("Удаляю старую базу данных для создания новой...")
                    import shutil
                    if os.path.exists(persist_directory):
                        try:
                            shutil.rmtree(persist_directory)
                            print(f"Старая база данных удалена: {persist_directory}")
                        except Exception as rm_error:
                            print(f"Ошибка при удалении базы: {rm_error}")
                    
                    # Пересоздаём клиент и коллекции
                    self.client = chromadb.PersistentClient(path=persist_directory)
                    self.collections[system] = self.client.get_or_create_collection(name=collection_name)
                    print(f"Новая коллекция '{collection_name}' создана успешно.")
                else:
                    # Если это другая ошибка, пробрасываем её дальше
                    raise
        
        # Инициализируем модель GPT4All. Она скачает модель при первом запуске.
        print("Инициализирую модель GPT4All для эмбеддингов...")
        self.embedding_model = GPT4AllEmbeddings()
        print("Модель GPT4All готова к работе.")
    
    def detect_system_from_query(self, query: str) -> str | None:
        """
        Определяет систему из запроса пользователя.
        
        Returns:
            "asupgr", "digital_twin" или None (если не удалось определить)
        """
        query_lower = query.lower()
        
        # Ключевые слова для АСУ ПГР
        asupgr_keywords = [
            "асу пгр", "асупгр", "пгр", "планово-геологический",
            "планово геологический", "планово-геологическая", "планово геологическая"
        ]
        
        # Ключевые слова для Цифрового двойника
        digital_twin_keywords = [
            "цифровой двойник", "цифрового двойника", "цифровому двойнику",
            "цифровым двойником", "двойник", "карьер", "экскаватор", "самосвал",
            "бульдозер", "склад", "складской", "склада"
        ]
        
        # Проверяем наличие ключевых слов
        asupgr_score = sum(1 for keyword in asupgr_keywords if keyword in query_lower)
        digital_twin_score = sum(1 for keyword in digital_twin_keywords if keyword in query_lower)
        
        if asupgr_score > 0 and asupgr_score >= digital_twin_score:
            return "asupgr"
        elif digital_twin_score > 0:
            return "digital_twin"
        
        # Если не удалось определить, возвращаем None (будет использоваться общий поиск)
        return None

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
        """Читает все .pdf, .docx и .md файлы из папки 'data' и возвращает единый текст."""
        data_folder = "data"
        all_texts = []
        print("Загрузка данных из локальной папки 'data'...")
        
        try:
            for filename in os.listdir(data_folder):
                file_path = os.path.join(data_folder, filename)
                print(f"  Обрабатываю файл: {filename}")

                if filename.endswith(".pdf"):
                    try:
                        loader = PyPDFLoader(file_path)
                        documents = loader.load()
                        text_content = "\n\n".join([doc.page_content for doc in documents])
                        all_texts.append(text_content)
                    except Exception as e:
                        print(f"    ОШИБКА при чтении PDF {filename}: {e}")

                elif filename.endswith(".docx"):
                    try:
                        loader = Docx2txtLoader(file_path)
                        documents = loader.load()
                        text_content = documents[0].page_content
                        all_texts.append(text_content)
                    except Exception as e:
                        print(f"    ОШИБКА при чтении DOCX {filename}: {e}")
                
                elif filename.lower().endswith(".md"):
                    try:
                        loader = TextLoader(file_path, encoding="utf-8")
                        documents = loader.load()
                        text_content = "\n\n".join([doc.page_content for doc in documents])
                        all_texts.append(text_content)
                    except Exception as e:
                        print(f"    ОШИБКА при чтении MD {filename}: {e}")
                
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
            print("    В папке 'data' не найдено поддерживаемых документов (.pdf, .docx, .md).")
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

    def create_knowledge_base(self, system: str = None):
        """
        Индексирует все знания из Git, Confluence и локальных файлов в векторную базу для указанной системы.
        
        Args:
            system: "asupgr" или "digital_twin". Если None, индексирует обе системы.
        """
        systems_to_index = [system] if system else ["asupgr", "digital_twin"]
        
        for sys in systems_to_index:
            if sys not in self.collections:
                print(f"Пропускаю неизвестную систему: {sys}")
                continue
                
            print(f"\n{'='*60}")
            print(f"Начинаю индексацию базы знаний для системы: {sys.upper()}")
            print(f"{'='*60}")
            
            # 1. Загружаем данные из Git для конкретной системы
            print(f"Загрузка данных из Git для {sys}...")
            git_text = load_git_knowledge(system=sys)

            # Вызываем функцию для загрузки всех данных из Confluence (если нужно)
            confluence_text = self._load_all_confluence_data()

            # Вызываем функцию для загрузки локальных файлов (если нужно)
            local_text = self._load_local_files()
            
            # 2. Объединяем все тексты в один
            full_text = (
                f"--- ИНФОРМАЦИЯ ИЗ GIT [{sys.upper()}] ---\n{git_text}\n\n"
                f"--- ИНФОРМАЦИЯ ИЗ CONFLUENCE ---\n{confluence_text}\n\n"
                f"--- ИНФОРМАЦИЯ ИЗ ЛОКАЛЬНЫХ ФАЙЛОВ ---\n{local_text}"
            )
            
            if not git_text.strip() and not confluence_text.strip() and not local_text.strip():
                print(f"   Предупреждение: Нет данных для системы {sys}. Пропускаю индексацию.")
                continue
            
            # 3. Разбиваем на чанки
            chunks = self._chunk_text(full_text)
            print(f"Текст разбит на {len(chunks)} чанков для системы {sys}.")
            
            # 4. Очищаем старую коллекцию для этой системы
            collection_name = f"{sys}_knowledge"
            try:
                self.client.delete_collection(name=collection_name)
            except:
                pass  # Коллекция может не существовать
            self.collections[sys] = self.client.get_or_create_collection(name=collection_name)
            
            # 5. Создаем эмбеддинги для всех чанков
            print(f"Создаю эмбеддинги для чанков системы {sys}... Это может занять время.")
            embeddings = self.embedding_model.embed_documents(chunks)
            
            # 6. Добавляем в базу
            ids = [f"{sys}_{i}" for i in range(len(chunks))]
            self.collections[sys].add(
                documents=chunks,
                embeddings=embeddings,
                ids=ids
            )
            print(f"База знаний для системы {sys} успешно проиндексирована. Добавлено {len(chunks)} документов.")

    def search_relevant_knowledge(self, query: str, n_results: int = 80, system: str = None) -> str:
        """
        Ищет релевантные чанки по запросу пользователя в указанной системе.
        
        Args:
            query: Текст запроса
            n_results: Количество результатов для поиска
            system: "asupgr" или "digital_twin". Если None, пытается определить автоматически.
        
        Returns:
            Текст с релевантными чанками
        """
        # Если система не указана, пытаемся определить из запроса
        if system is None:
            system = self.detect_system_from_query(query)
        
        print(f"Ищу релевантную информацию по запросу: '{query}'")
        if system:
            print(f"Использую базу знаний для системы: {system}")
        else:
            print("Система не определена, ищу в обеих базах знаний.")
        
        query_embedding = self.embedding_model.embed_query(query)
        
        # Если система определена, ищем только в её базе
        if system and system in self.collections:
            collection_name = f"{system}_knowledge"

            def _run_query() -> dict:
                return self.collections[system].query(
                    query_embeddings=[query_embedding],
                    n_results=n_results
                )

            try:
                results = _run_query()
            except Exception as e:
                if "Collection" in str(e) and "does not exist" in str(e):
                    print(f"Коллекция {collection_name} не найдена. Переинициализирую...")
                    self.collections[system] = self.client.get_or_create_collection(name=collection_name)
                    results = _run_query()
                else:
                    raise
            
            if not results['documents'] or not results['documents'][0]:
                return "Релевантная информация в базе знаний не найдена."
                
            retrieved_chunks = results['documents'][0]
            context = "\n\n---\n\n".join(retrieved_chunks)
            print(f"Найдено {len(retrieved_chunks)} релевантных чанков в базе {system}.")
            return context
        else:
            # Если система не определена, ищем в обеих базах и объединяем результаты
            all_chunks = []
            for sys in ["asupgr", "digital_twin"]:
                if sys in self.collections:
                    results = self.collections[sys].query(
                        query_embeddings=[query_embedding],
                        n_results=n_results // 2  # Делим результаты пополам
                    )
                    if results['documents'] and results['documents'][0]:
                        all_chunks.extend(results['documents'][0])
            
            if not all_chunks:
                return "Релевантная информация в базе знаний не найдена."
            
            context = "\n\n---\n\n".join(all_chunks)
            print(f"Найдено {len(all_chunks)} релевантных чанков в обеих базах.")
            return context