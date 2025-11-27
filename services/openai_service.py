"""OpenAI/OpenRouter service for text generation."""
import requests
import json
import os
from dotenv import load_dotenv, find_dotenv

# Загружаем переменные окружения
load_dotenv(find_dotenv())

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

if not OPENROUTER_API_KEY:
    print("ПРЕДУПРЕЖДЕНИЕ: OPENROUTER_API_KEY не найден в переменных окружения.")


class LLMError(Exception):
    """Кастомный класс для ошибок LLM."""
    pass


def generate_text(prompt: str, model: str = "kwaipilot/kat-coder-pro:free") -> str:
    """Генерирует текст с помощью OpenRouter API."""
    print(f"Отправляю запрос в OpenRouter (модель: {model})...")
    
    # Проверяем ключ еще раз перед отправкой
    if not OPENROUTER_API_KEY:
        raise LLMError("API ключ не загружен. Проверьте переменную OPENROUTER_API_KEY в .env файле.")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        # Разрешаем модели генерировать длинные развёрнутые ответы (подробные ТЗ/руководства)
        "max_tokens": 4000,
    }
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        response_text = response.text
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            print("Предупреждение: Получен невалидный JSON. Попытка исправить...")
            import re
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                cleaned_json = match.group(0)
                response_json = json.loads(cleaned_json)
                print("JSON успешно исправлен.")
            else:
                raise LLMError("Не удалось найти валидный JSON в ответе сервера.")
        
        if 'choices' in response_json and len(response_json['choices']) > 0 and 'message' in response_json['choices'][0]:
            generated_text = response_json['choices'][0]['message']['content']
            print("Ответ от OpenRouter получен и успешно разобран.")
            return generated_text
        else:
            raise LLMError("Неверная структура ответа от API.")

    except requests.exceptions.RequestException as e:
        raise LLMError(f"Ошибка API: {e}")
    except Exception as e:
        raise LLMError(f"Непредвиденная ошибка: {e}")
