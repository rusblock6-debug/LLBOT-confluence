# services/confluence_service.py (УЛУЧШЕННАЯ ВЕРСИЯ С ГЛОССАРИЕМ)
from atlassian import Confluence
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests # Добавим для прямого обращения к API

load_dotenv()

CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
SPACE_KEY = os.getenv("SPACE_KEY")

# Используем сессию для прямых запросов к API Confluence
auth = (CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)

# --- НОВАЯ ФУНКЦИЯ ДЛЯ ГЛОССАРИЯ ---
def load_glossary_from_confluence() -> dict:
    """Загружает глоссарий из таблиц Confluence в словарь."""
    print("Загружаю глоссарий из Confluence...")
    glossary = {}
    url = f"{CONFLUENCE_URL}/rest/api/content"
    params = {"spaceKey": SPACE_KEY, "limit": 50, "expand": "body.storage"}
    
    try:
        while True:
            response = requests.get(url, params=params, auth=auth)
            response.raise_for_status()
            data = response.json()
            
            for page in data.get("results", []):
                title = page["title"]
                html = page["body"]["storage"]["value"]
                
                # Парсинг таблиц, как в вашем примере
                soup = BeautifulSoup(html, "lxml")
                for table in soup.find_all("table"):
                    for tr in table.find_all("tr"):
                        cols = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
                        if len(cols) >= 2:
                            term = cols[0].upper()
                            definition = " ".join(cols[1:])
                            glossary[term] = definition
            
            if "_links" in data and "next" in data["_links"]:
                url = CONFLUENCE_URL + data["_links"]["next"]
                params = None
            else:
                break
                
    except Exception as e:
        print(f"Ошибка при загрузке глоссария: {e}")
        
    print(f"Загружено {len(glossary)} терминов в глоссарий.")
    return glossary

# --- СТАРАЯ ФУНКЦИЯ ДЛЯ ПОИСКА (остается для общих запросов) ---
def search_confluence(query: str, limit: int = 5) -> str:
    """Ищет в Confluence страницы по запросу и возвращает их текст."""
    print(f"Ищу в Confluence по запросу: '{query}'...")
    try:
        confluence = Confluence(url=CONFLUENCE_URL, username=CONFLUENCE_USERNAME, password=CONFLUENCE_API_TOKEN, cloud=True)
        cql = f'text ~ "{query}" or title ~ "{query}"'
        response = confluence.cql(cql, limit=limit)
        
        if 'results' not in response or not response['results']:
            print("   В Confluence ничего не найдено.")
            return ""
            
        results = response['results']
        full_text = ""
        for page in results:
            if 'id' in page and 'title' in page:
                title = page['title']
                content = confluence.get_page_by_id(page['id'], expand='body.storage')['body']['storage']['value']
                soup = BeautifulSoup(content, "html.parser")
                text_content = soup.get_text(separator=' ', strip=True)
                full_text += f"--- Confluence Page: {title} ---\n{text_content}\n\n"
        
        print(f"   Обработано {len(results)} страниц из Confluence.")
        return full_text

    except Exception as e:
        print(f"   Ошибка при поиске в Confluence: {e}")
        return ""