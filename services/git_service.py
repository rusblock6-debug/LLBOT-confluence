# services/git_service.py (ИСЛЕДЕННАЯ, 100% ПРАВИЛЬНАЯ ВЕРСИЯ)
import requests
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")

def list_md_files_from_git() -> list:
    """
    Получает список всех .md файлов из нужных папок в репозитории.
    """
    # Вот эти папки. Они лежат ВНУТРИ 'docs' РЯДОМ друг с другом.
    dirs_to_search = ["architecture", "blocks", "functions", "glossary", "user_scenarios"]
    all_files = []
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    for dir_name in dirs_to_search:
        path_to_search = f"docs/{dir_name}"
        api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO_NAME}/contents/{path_to_search}"
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            items = response.json()
            for item in items:
                if item['type'] == 'file' and item['name'].endswith('.md'):
                    all_files.append(item['path'])
        except Exception as e:
            print(f"   -> Не удалось получить файлы из папки {path_to_search}: {e}")

    return all_files

def load_git_knowledge() -> str:
    """Загружает текст из всех .md файлов в Git."""
    print("Загружаю знания из Git (чтение .md файлов из всех нужных папок)...")
    
    md_files = list_md_files_from_git()
    if not md_files:
        print("Не найдено .md файлов в репозитории.")
        return ""
        
    print(f"Найдено {len(md_files)} .md файлов. Начинаю загрузку...")
    
    full_text = ""
    for file_path in md_files:
        try:
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO_NAME}/main/{file_path}"
            response = requests.get(raw_url)
            response.raise_for_status()
            content = response.text
            full_text += f"--- ФАЙЛ: {file_path} ---\n\n{content}\n\n"
            
        except Exception as e:
            print(f"   !!! Ошибка при загрузке файла {file_path}: {e}")
            
    print(f"Загрузка из Git завершена. Общий размер: {len(full_text)} символов.")
    return full_text