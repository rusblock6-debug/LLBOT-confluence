# bot.py (УПРОЩЕННАЯ ВЕРСИЯ БЕЗ КНОПКИ "НАЗАД")
import os
import requests
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ORCHESTRATOR_URL = "http://127.0.0.1:8000/process"
FEEDBACK_URL = "http://127.0.0.1:8000/feedback"

# --- Определяем клавиатуры ---
main_keyboard = [
    [KeyboardButton('📄 Документ'), KeyboardButton('📝 Термин')],
    [KeyboardButton('✏️ Правка')]
]
main_markup = ReplyKeyboardMarkup(main_keyboard, one_time_keyboard=True, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветствие и главную клавиатуру."""
    # Сбрасываем предыдущее действие пользователя
    context.user_data['action'] = None
    await update.message.reply_text(
        'Привет! Я помогу тебе создать документ или найти определение термина. '
        'Выбери, что ты хочешь сделать:',
        reply_markup=main_markup
    )


async def process_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user_query: str, request_type: str, template_name: str = None) -> None:
    """Универсальная функция для отправки запроса на API и обработки ответа."""
    await update.message.reply_text(f'Принял запрос: "{user_query}". Начинаю обработку...')
    if template_name:
        await update.message.reply_text(f'Использую шаблон: {template_name}')
    
    docx_path = None
    
    try:
        # Готовим payload для API
        payload = {"query": user_query, "request_type": request_type}
        if template_name:
            payload["template_name"] = template_name

        response = requests.post(ORCHESTRATOR_URL, json=payload)
        response.raise_for_status()
        
        result_info = response.json()
        
        if result_info.get("status") == "success":
            result_type = result_info.get("result_type")

            if result_type == "term":
                term = result_info.get("term")
                definition = result_info.get("definition")
                await update.message.reply_text(f'**Определение термина "{term}":**\n\n{definition}', parse_mode='Markdown')

            elif result_type == "document":
                docx_path = result_info.get("file_path")
                if docx_path and os.path.exists(docx_path):
                    with open(docx_path, 'rb') as doc:
                        await update.message.reply_document(document=doc, caption="Готово! Ваш документ.")
                else:
                    await update.message.reply_text("Сервер сообщил об успехе, но файл не найден.")
            elif result_type == "qa":
                answer = result_info.get("answer", "")
                if not answer:
                    answer = "Ответ на вопрос не получен от сервера."
                await update.message.reply_text(answer)
        else:
            error_message = result_info.get("message", "Неизвестная ошибка на сервере.")
            await update.message.reply_text(f'Не удалось обработать запрос. Причина: {error_message}')

    except Exception as e:
        await update.message.reply_text(f'Произошла ошибка связи с сервером: {e}')
        print(f"--- ОШИБКА В БОТЕ ---\n{e}")
    
    finally:
        # Удаляем временный файл, если он был создан
        if docx_path and os.path.exists(docx_path):
            os.remove(docx_path)
            print("Временный файл удален.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Универсальный обработчик для всех текстовых сообщений."""
    user_text = update.message.text
    current_action = context.user_data.get('action')

    # --- Если пользователь в главном меню ---
    if current_action is None:
        if '📄 Документ' in user_text:
            context.user_data['action'] = 'document'
            await update.message.reply_text(
                'Отлично! Введи текст для создания документа.\n\n'
                'Если хочешь использовать шаблон, напиши в формате:\n'
                '"Ваш запрос" по шаблону Имя_файла_шаблона.doc'
            )
        elif '📝 Термин' in user_text:
            context.user_data['action'] = 'term'
            await update.message.reply_text('Хорошо! Введи термин для поиска.')
        elif '✏️ Правка' in user_text:
            # Запускаем диалог по сбору правки
            context.user_data['action'] = 'feedback'
            context.user_data['feedback_step'] = 1
            context.user_data['feedback_data'] = {}
            await update.message.reply_text(
                'Режим правки документации.\n'
                'Шаг 1/6: Укажи тип документа (например: ТЗ, Руководство, Глоссарий, Другое).'
            )
        else:
            # Пользователь ввел текст сразу, считаем что он хочет документ
            await process_request(update, context, user_text, 'document')
            # Состояние не менялось, так что сбрасывать не нужно
            await update.message.reply_text('Выбери следующее действие:', reply_markup=main_markup)
    else:
        # --- Пользователь уже выбрал действие и вводит запрос ---
        if current_action == 'feedback':
            # Многошаговый сбор данных для правки
            step = context.user_data.get('feedback_step', 1)
            data = context.user_data.get('feedback_data', {})

            if step == 1:
                data['doc_type'] = user_text
                context.user_data['feedback_step'] = 2
                context.user_data['feedback_data'] = data
                await update.message.reply_text('Шаг 2/6: Укажи документ или раздел (файл, пункт, краткое описание).')
                return

            if step == 2:
                data['doc_ref'] = user_text
                context.user_data['feedback_step'] = 3
                context.user_data['feedback_data'] = data
                await update.message.reply_text(
                    'Шаг 3/6: Укажи тип операции: удалить / заменить / добавить / комментарий.'
                )
                return

            if step == 3:
                op_text = user_text.strip().lower()
                if 'удал' in op_text:
                    data['operation'] = 'delete'
                elif 'замен' in op_text:
                    data['operation'] = 'replace'
                elif 'добав' in op_text:
                    data['operation'] = 'add'
                else:
                    data['operation'] = 'comment'

                context.user_data['feedback_step'] = 4
                context.user_data['feedback_data'] = data
                await update.message.reply_text('Шаг 4/6: Напиши текст, который БЫЛО (если нечего указывать, напиши "-").')
                return

            if step == 4:
                data['old_text'] = user_text
                context.user_data['feedback_step'] = 5
                context.user_data['feedback_data'] = data
                await update.message.reply_text('Шаг 5/6: Напиши текст, который ДОЛЖНО БЫТЬ (или "-", если только удаление/комментарий).')
                return

            if step == 5:
                data['new_text'] = user_text
                context.user_data['feedback_step'] = 6
                context.user_data['feedback_data'] = data
                await update.message.reply_text('Шаг 6/6: Добавь краткий комментарий для себя/команды (или "-").')
                return

            if step == 6:
                data['comment'] = user_text

                # Формируем payload для /feedback
                author = update.effective_user.username or update.effective_user.full_name
                payload = {
                    "author": author,
                    "doc_type": data.get('doc_type'),
                    "doc_ref": data.get('doc_ref'),
                    "operation": data.get('operation'),
                    "old_text": data.get('old_text'),
                    "new_text": data.get('new_text'),
                    "comment": data.get('comment'),
                }

                try:
                    resp = requests.post(FEEDBACK_URL, json=payload)
                    resp.raise_for_status()
                    info = resp.json()
                    if info.get('status') == 'success':
                        fp = info.get('file_path', '-')
                        await update.message.reply_text(
                            f'Правка сохранена локально. Файл: {fp}\n'
                            f'Ты сможешь потом внести изменения в Git, ориентируясь на этот файл.'
                        )
                    else:
                        await update.message.reply_text(
                            f"Не удалось сохранить правку. Ответ сервера: {info.get('message', 'без сообщения')}"
                        )
                except Exception as e:
                    await update.message.reply_text(f'Ошибка при отправке правки: {e}')

                # Сбрасываем состояние и возвращаемся в главное меню
                context.user_data['action'] = None
                context.user_data.pop('feedback_step', None)
                context.user_data.pop('feedback_data', None)
                await update.message.reply_text('Правка зафиксирована. Что-нибудь еще?', reply_markup=main_markup)
                return

        # --- Обычные режимы: документ / термин ---
        request_type = current_action
        user_query = user_text
        template_name = None

        if request_type == 'document':
            if "по шаблону" in user_query.lower():
                try:
                    parts = user_query.split("по шаблону")
                    user_query = parts[0].strip()
                    template_name = parts[1].strip()
                except IndexError:
                    await update.message.reply_text("Неверный формат для указания шаблона. Попробуй еще раз.")
                    return

        # Вызываем обработку запроса
        await process_request(update, context, user_query, request_type, template_name)
        
        # --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Возвращаем в главное меню ---
        context.user_data['action'] = None
        await update.message.reply_text('Что-нибудь еще?', reply_markup=main_markup)


if __name__ == '__main__':
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).connect_timeout(30.0).read_timeout(30.0).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("Telegram-бот запущен...")
    application.run_polling()