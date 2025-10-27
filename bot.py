# bot.py (ПОЛНАЯ ФИНАЛЬНАЯ ВЕРСИЯ)
import os
import requests
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ORCHESTRATOR_URL = "http://127.0.0.1:8000/generate"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Отправляй запрос.')

async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_query = update.message.text
    await update.message.reply_text(f'Принял запрос: "{user_query}". Начинаю обработку...')
    
    docx_path = None
    
    try:
        response = requests.post(ORCHESTRATOR_URL, json={"query": user_query})
        response.raise_for_status()
        
        result_info = response.json()
        
        # Проверяем статус, который вернул сервер
        if result_info.get("status") == "success":
            docx_path = result_info.get("file_path")
            if docx_path and os.path.exists(docx_path):
                with open(docx_path, 'rb') as doc:
                    await update.message.reply_document(document=doc, caption="Готово! Ваш документ.")
            else:
                await update.message.reply_text("Сервер сообщил об успехе, но файл не найден.")
        else:
            # Если сервер вернул ошибку, сообщаем ее пользователю
            error_message = result_info.get("message", "Неизвестная ошибка на сервере.")
            await update.message.reply_text(f'Не удалось создать документ. Причина: {error_message}')

    except Exception as e:
        await update.message.reply_text(f'Произошла ошибка связи с сервером: {e}')
        print(f"--- ОШИБКА В БОТЕ ---")
        print(e)
    
    finally:
        # Удаляем временный файл, если он был создан
        if docx_path and os.path.exists(docx_path):
            os.remove(doc_path)
            print("Временный файл удален.")

if __name__ == '__main__':
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).connect_timeout(30.0).read_timeout(30.0).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_request))
    
    print("Telegram-бот запущен...")
    application.run_polling()