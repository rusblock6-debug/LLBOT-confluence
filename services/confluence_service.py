# services/confluence_service.py
from atlassian import Confluence
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")

confluence = Confluence(
    url=CONFLUENCE_URL,
    username=CONFLUENCE_USERNAME,
    password=CONFLUENCE_API_TOKEN,
    cloud=True
)

def search_confluence(query: str, limit: int = 5) -> str:
    """Ищет в Confluence страницы по запросу и возвращает их текст."""
    print(f"Ищу в Confluence по запросу: '{query}'...")
    try:
        cql = f'text ~ "{query}" or title ~ "{query}"'
        results = confluence.cql(cql, limit=limit)['results']
        
        full_text = ""
        for page in results:
            title = page['title']
            content = confluence.get_page_by_id(page['id'], expand='body.storage')['body']['storage']['value']
            soup = BeautifulSoup(content, "html.parser")
            text_content = soup.get_text(separator=' ', strip=True)
            
            full_text += f"--- Confluence Page: {title} ---\n{text_content}\n\n"
        
        print(f"Найдено {len(results)} страниц в Confluence.")
        return full_text

    except Exception as e:
        print(f"Ошибка при поиске в Confluence: {e}")
        return ""