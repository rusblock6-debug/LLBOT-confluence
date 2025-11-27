# services/git_service.py (Обновленная версия с поддержкой двух систем и изображений)
import os
from typing import List, Dict, Tuple
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")

# Настройки корневых папок для систем
# При необходимости пути можно вынести в .env
SYSTEM_CONFIG = {
    "asupgr": {
        "doc_paths": [
            "АСУ_ПГР/АСУ-ПГР-ОПИСАНИЕ СИСТЕМЫ-КРАТКОЕ/docs"
        ],
        "image_paths": []
    },
    "digital_twin": {
        "doc_paths": [
            "Цифровой двойник/docs"
        ],
        "image_paths": [
            "Цифровой двойник/screenshots",
            "Цифровой двойник/images"
        ]
    }
}


def _build_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def _fetch_directory_contents(path: str, headers: Dict[str, str]) -> List[Dict[str, str]]:
    """Возвращает содержимое директории GitHub (пустой список, если нет)."""
    encoded_path = quote(path, safe="/")
    api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO_NAME}/contents/{encoded_path}"
    response = requests.get(api_url, headers=headers)

    if response.status_code == 404:
        print(f"   -> Папка не найдена: {path}")
        return []

    response.raise_for_status()
    items = response.json()
    if not isinstance(items, list):
        return []
    return items


def _collect_files_recursive(base_path: str, extensions: List[str], headers: Dict[str, str]) -> List[str]:
    """
    Рекурсивно собирает файлы с указанными расширениями, начиная с base_path.

    Args:
        base_path: путь в репозитории, с которого стартуем обход
        extensions: список расширений в нижнем регистре (например, ['.md']). Пустой список => любые файлы.
        headers: заголовки запроса
    """
    if not base_path:
        return []

    stack = [base_path]
    collected: List[str] = []

    while stack:
        current = stack.pop()
        items = _fetch_directory_contents(current, headers)

        for item in items:
            item_type = item.get("type")
            item_path = item.get("path")
            item_name = item.get("name", "")

            if not item_path:
                continue

            if item_type == "dir":
                stack.append(item_path)
                continue

            if item_type == "file":
                ext = os.path.splitext(item_name)[1].lower()
                if not extensions or ext in extensions:
                    collected.append(item_path)

    return collected


def list_md_files_from_git(system: str = None) -> List[Tuple[str, str]]:
    """
    Получает список всех .md файлов из нужных папок в репозитории для указанной системы.

    Args:
        system: "asupgr" или "digital_twin". Если None, возвращает файлы из обеих систем.
    """
    all_files: List[Tuple[str, str]] = []
    headers = _build_headers()

    systems_to_search = [system] if system else list(SYSTEM_CONFIG.keys())

    for sys in systems_to_search:
        config = SYSTEM_CONFIG.get(sys)
        if not config:
            print(f"   -> Неизвестная система: {sys}. Пропускаю.")
            continue

        doc_paths = config.get("doc_paths", [])
        if not doc_paths:
            print(f"   -> Для системы {sys} не указаны doc_paths. Пропускаю.")
            continue

        for base_path in doc_paths:
            print(f"   -> Сканирую markdown для системы '{sys}' из '{base_path}'")
            try:
                files = _collect_files_recursive(base_path, extensions=[".md"], headers=headers)
                all_files.extend((path, sys) for path in files)
            except requests.HTTPError as e:
                print(f"   -> Ошибка при загрузке данных из {base_path}: {e}")

    return all_files


def list_image_files_from_git(system: str = None) -> List[Tuple[str, str]]:
    """
    Получает список всех изображений из репозитория для указанной системы.

    Args:
        system: "asupgr" или "digital_twin". Если None, возвращает изображения из обеих систем.

    Returns:
        Список кортежей (путь_к_файлу, система)
    """
    headers = _build_headers()
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']

    all_images = []

    systems_to_search = [system] if system else list(SYSTEM_CONFIG.keys())

    for sys in systems_to_search:
        config = SYSTEM_CONFIG.get(sys)
        if not config:
            continue

        image_paths = config.get("image_paths", [])
        if not image_paths:
            continue

        for base_path in image_paths:
            try:
                files = _collect_files_recursive(base_path, extensions=image_extensions, headers=headers)
                for path in files:
                    name = os.path.basename(path)
                    all_images.append((path, sys, name))
            except requests.HTTPError:
                # Папка может отсутствовать — не критично
                print(f"   -> Не удалось получить изображения из {base_path}")

    return all_images


def load_git_knowledge(system: str = None) -> str:
    """
    Загружает текст из всех .md файлов в Git для указанной системы.

    Args:
        system: "asupgr" или "digital_twin". Если None, загружает из обеих систем.
    """
    system_label = f" ({system})" if system else " (все системы)"
    print(f"Загружаю знания из Git{system_label} (чтение .md файлов из всех нужных папок)...")

    md_files = list_md_files_from_git(system=system)
    if not md_files:
        print("Не найдено .md файлов в репозитории.")
        return ""

    print(f"Найдено {len(md_files)} .md файлов. Начинаю загрузку...")

    full_text = ""
    for file_path, sys in md_files:
        try:
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO_NAME}/main/{file_path}"
            response = requests.get(raw_url)

            response.raise_for_status()
            content = response.text
            full_text += f"--- ФАЙЛ [{sys.upper()}]: {file_path} ---\n\n{content}\n\n"

        except Exception as e:
            print(f"   !!! Ошибка при загрузке файла {file_path}: {e}")

            
    print(f"Загрузка из Git завершена. Общий размер: {len(full_text)} символов.")
    return full_text

def search_images_by_keywords(keywords: List[str], system: str = None) -> List[Dict[str, str]]:
    """
    Ищет изображения по ключевым словам в названии файла.
    
    Args:
        keywords: Список ключевых слов для поиска (например, ["экскаватор", "создание"])
        system: "asupgr" или "digital_twin". Если None, ищет в обеих системах.
    
    Returns:
        Список словарей с информацией об изображениях: [{"url": "...", "name": "...", "system": "..."}]
    """
    all_images = list_image_files_from_git(system=system)
    matched_images = []
    
    keywords_lower = [kw.lower() for kw in keywords]
    
    for img_path, sys, img_name in all_images:
        img_name_lower = img_name.lower()
        # Убираем фигурные скобки и другие символы для более точного поиска
        img_name_clean = img_name_lower.replace('{', '').replace('}', '').replace('_', ' ').replace('-', ' ')
        # Проверяем, содержит ли название файла хотя бы одно ключевое слово
        if any(kw in img_name_lower or kw in img_name_clean for kw in keywords_lower):
            # Формируем URL для raw изображения
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO_NAME}/main/{img_path}"
            matched_images.append({
                "url": raw_url,
                "name": img_name,
                "path": img_path,
                "system": sys
            })
    
    return matched_images