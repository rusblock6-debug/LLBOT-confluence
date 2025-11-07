# services/confluence_service.py
import os
from atlassian import Confluence
from dotenv import load_dotenv

load_dotenv()

# --- Настройки подключения к Confluence ---
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
SPACE_KEY = os.getenv("SPACE_KEY")

# Инициализация клиента
try:
    confluence = Confluence(
        url=CONFLUENCE_URL,
        username=CONFLUENCE_USERNAME,
        password=CONFLUENCE_API_TOKEN,
        cloud=True  # Важно для Atlassian Cloud
    )
    print("Клиент Confluence успешно инициализирован.")
except Exception as e:
    print(f"ОШИБКА: Не удалось инициализировать клиент Confluence: {e}")
    confluence = None

def search_confluence(query: str, limit: int = 10) -> str:
    """
    Ищет в Confluence по запросу и возвращает объединенный текст найденных страниц.
    """
    if not confluence:
        print("Клиент Confluence не доступен. Поиск не выполнен.")
        return ""
    
    print(f"Ищу в Confluence по запросу: '{query}'...")
    try:
        results = confluence.cql(
            cql=f"space='{SPACE_KEY}' and text ~ '{query}'",
            limit=limit,
            expand='body.storage'
        )
        
        if not results:
            print("   В Confluence ничего не найдено.")
            return ""

        combined_text = ""
        for page in results:
            title = page.get('title', 'Без заголовка')
            content = page.get('body', {}).get('storage', {}).get('value', '')
            combined_text += f"--- СТРАНИЦА: {title} ---\n{content}\n\n"
        
        print(f"   Найдено {len(results)} страниц в Confluence.")
        return combined_text.strip()

    except Exception as e:
        print(f"   Произошла ошибка при поиске в Confluence: {e}")
        return ""

def get_all_pages_from_space(space_key: str, limit: int = 50) -> list[str]:
    """
    Рекурсивно получает все страницы из указанного пространства Confluence.
    """
    if not confluence:
        print("Клиент Confluence не доступен. Загрузка всех страниц не выполнена.")
        return []

    all_content = []
    start = 0
    has_more = True

    print(f"  Скачивание страниц из пространства '{space_key}'...")
    while has_more:
        try:
            # Метод для получения страниц из пространства
            response = confluence.get_all_pages_from_space(
                space=space_key, 
                start=start, 
                limit=limit,
                expand='body.storage'
            )
            
            if not response:
                has_more = False
                break

            for page in response:
                title = page.get('title', 'Без заголовка')
                # Извлекаем текст из body.storage
                content = page.get('body', {}).get('storage', {}).get('value', '')
                if content:
                    formatted_page = f"--- СТРАНИЦА: {title} ---\n{content}"
                    all_content.append(formatted_page)
            
            # Проверяем, есть ли еще страницы
            if len(response) < limit:
                has_more = False
            else:
                start += limit
                print(f"    Загружено {len(all_content)} страниц, продолжаю...")

        except Exception as e:
            print(f"    ОШИБКА при получении страниц: {e}")
            has_more = False

    print(f"  Завершили загрузку. Всего страниц: {len(all_content)}")
    return all_content
