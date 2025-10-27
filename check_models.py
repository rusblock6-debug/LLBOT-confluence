import requests
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def get_available_models():
    url = "https://openrouter.ai/api/v1/models"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        models = response.json()
        print("Модели, доступные для вашего API-ключа:\n")
        
        free_models = []
        for model in models['data']:
            if model.get("pricing") and model["pricing"].get("prompt") == "0":
                model_id = model['id']
                model_name = model.get('name', 'No name')
                free_models.append(f"ID: {model_id} | Name: {model_name}")
        
        if not free_models:
            print("Для вашего ключа не найдено бесплатных моделей.")
        else:
            for model_info in free_models:
                print(model_info)

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")

if __name__ == '__main__':
    get_available_models()