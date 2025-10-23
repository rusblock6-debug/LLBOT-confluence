# services/git_service.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO_NAME")

def get_raw_url_from_github(path_in_repo: str) -> str:
    """Создает прямую ссылку на файл в репозитории."""
    return f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/{path_in_repo}"

def load_git_knowledge() -> str:
    """Загружает все текстовые данные из эмбеддинг-файлов Git."""
    print("Загружаю знания из Git...")
    base_path = "docs/architecture"
    files_to_load = [
        "architecture_combined.embeddings.json",
        "blocks_combined.embeddings.json",
        "functions_combined.embeddings.json",
        "glossary_combined.embeddings.json",
        "user_scenarios_combined.embeddings.json",
    ]
    
    full_text = ""
    for file_name in files_to_load:
        try:
            url = get_raw_url_from_github(f"{base_path}/{file_name}")
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
            for item in data:
                if 'text' in item:
                    full_text += item['text'] + "\n\n"
        except requests.exceptions.RequestException as e:
            print(f"Не удалось загрузить файл {file_name} из Git: {e}")
            
    print(f"Загружено {len(full_text)} символов из Git.")
    return full_text