# services/openai_service.py (адаптированный для OpenRouter)
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Инициализируем клиент OpenAI, но направляем его на серверы OpenRouter
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"  # <-- ВОТ ГЛАВНОЕ ИЗМЕНЕНИЕ
)

def generate_text(prompt: str, model: str = "tngtech/deepseek-r1t2-chimera:free") -> str:
    """
    Отправляет промпт в OpenRouter API (используя совместимую библиотеку OpenAI) и возвращает текст.
    """
    print(f"Отправляю запрос в OpenRouter (модель: {model})...")
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Ты — опытный технический писатель и аналитик."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        
        generated_text = response.choices[0].message.content
        print("Ответ от OpenRouter получен.")
        return generated_text
        
    except Exception as e:
        print(f"Ошибка при запросе к OpenRouter API: {e}")
        return f"Произошла ошибка при обращении к модели: {e}"