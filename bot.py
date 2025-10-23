# bot.py
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
    await update.message.reply_text('Привет! Я умный технический писатель. Отправь мне запрос, и я подготовлю документ.')

async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_query = update.message.text
    await update.message.reply_text(f'Принял запрос: "{user_query}". Начинаю обработку...')
    
    try:
        response = requests.post(ORCHESTRATOR_URL, json={"query": user_query})
        response.raise_for_status()
        
        result_info = response.json()
        file_path = result_info.get("file_path")

        if file_path and os.path.exists(file_path):
            await update.message.reply_document(document=open(file_path, 'rb'), caption="Готово! Ваш документ.")
            os.remove(file_path)
        else:
            await update.message.reply_text("Не удалось сгенерировать файл.")

    except Exception as e:
        await update.message.reply_text(f'Произошла ошибка: {e}')

if __name__ == '__main__':
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_request))
    
    print("Telegram-бот запущен...")
    application.run_polling()