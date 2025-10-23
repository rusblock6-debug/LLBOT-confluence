# services/ollama_service.py
import requests
import json

OLLAMA_API_URL = "http://localhost:11434/api/generate"

def generate_text(prompt: str, model: str = "llama3.1:8b") -> str:
    """Отправляет промпт в Ollama и возвращает сгенерированный текст."""
    print(f"Отправляю запрос в Ollama (модель: {model})...")
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
        }
    }
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        generated_text = result.get("response", "")
        print("Ответ от Ollama получен.")
        return generated_text
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к Ollama: {e}")
        return f"Произошла ошибка при обращении к модели Ollama: {e}"