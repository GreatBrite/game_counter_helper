import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from telegram.error import TelegramError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
load_dotenv()
from config import (
    BOT_TOKEN, CHANNEL_ID, START_DATE, SEND_TIME, MESSAGE_TEMPLATE,
    BOSS_USERNAME, BOSS_CHAT_ID, VACATION_HASHTAG
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные
application = None
bot = None
scheduler = AsyncIOScheduler()
# Словарь для хранения состояния выходного дня: {date: is_vacation}
vacation_status = {}

def calculate_day_number():
    today = datetime.now().date()
    start_date = START_DATE.date()
    delta = today - start_date
    return delta.days + 1

def is_boss_user(update: Update) -> bool:
    """Проверяет, является ли пользователь боссом"""
    if not update.effective_user:
        return False
    username = update.effective_user.username
    return username and username.lower() == BOSS_USERNAME.lower()

async def check_and_send_message():
    try:
        current_day = calculate_day_number()
        today = datetime.now().date()
        
        logger.info(f"Проверяем сообщения за {today}")
        
        messages = []
        try:
            # Добавляем таймаут для запроса
            updates = await asyncio.wait_for(bot.get_updates(timeout=5), timeout=10)
            for update in updates:
                if hasattr(update, 'message') and update.message:
                    if update.message.chat.id == int(CHANNEL_ID.replace('-', '')):
                        messages.append(update.message)
        except asyncio.TimeoutError:
            logger.warning("Таймаут при получении сообщений - пропускаем проверку")
            messages = []
        except Exception as e:
            logger.error(f"Ошибка получения сообщений: {e}")
            messages = []
        
        message_sent_today = False
        
        for message in messages:
            if hasattr(message, 'date') and hasattr(message, 'text'):
                message_date = message.date.date()
                if message_date == today and message.text:
                    if "Разрабатываю игру день" in message.text:
                        message_sent_today = True
                        logger.info("Найдено сообщение за сегодня - пропускаем отправку")
                        break
        
        if not message_sent_today:
            message_text = MESSAGE_TEMPLATE.format(current_day)
            
            # Проверяем, является ли сегодня выходным
            is_vacation = vacation_status.get(today, False)
            if is_vacation:
                message_text += VACATION_HASHTAG
                logger.info(f"Добавлен хештег выходного для {today}")
            
            await bot.send_message(chat_id=CHANNEL_ID, text=message_text)
            logger.info(f"Отправлено сообщение: {message_text}")
            
            # Очищаем статус выходного после отправки
            if today in vacation_status:
                del vacation_status[today]
        else:
            logger.info("Сообщение уже было отправлено сегодня")
            
    except TelegramError as e:
        logger.error(f"Ошибка Telegram: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")

async def ask_about_vacation():
    """Отправляет вопрос о выходном боссу"""
    try:
        if not BOSS_CHAT_ID:
            logger.warning("BOSS_CHAT_ID не задан, пропускаем отправку вопроса")
            return
        
        keyboard = [
            [
                InlineKeyboardButton("Да", callback_data="vacation_yes"),
                InlineKeyboardButton("Нет", callback_data="vacation_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await bot.send_message(
            chat_id=BOSS_CHAT_ID,
            text="Босс, сегодня выходной?",
            reply_markup=reply_markup
        )
        logger.info("Отправлен вопрос о выходном боссу")
    except TelegramError as e:
        logger.error(f"Ошибка при отправке вопроса о выходном: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке вопроса: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия на кнопки"""
    query = update.callback_query
    await query.answer()
    
    # Проверяем, что это босс
    if not is_boss_user(update):
        await query.edit_message_text("У вас нет прав для выполнения этого действия.")
        logger.warning(f"Попытка использовать кнопки от неавторизованного пользователя: {update.effective_user.username}")
        return
    
    today = datetime.now().date()
    
    if query.data == "vacation_yes":
        vacation_status[today] = True
        await query.edit_message_text(
            "Понял, Босс, отдыхайте и набирайтесь сил, сегодня неплохой для этого день"
        )
        logger.info(f"Установлен выходной для {today}")
    elif query.data == "vacation_no":
        vacation_status[today] = False
        await query.edit_message_text(
            "Отлично, Босс, не перетруждайтесь, продуктивного Вам дня!"
        )
        logger.info(f"Выходной не установлен для {today}")

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команды, проверяя права доступа"""
    if not is_boss_user(update):
        await update.message.reply_text("У вас нет прав для выполнения команд.")
        logger.warning(f"Попытка выполнить команду от неавторизованного пользователя: {update.effective_user.username}")
        return
    
    command = update.message.text.split()[0] if update.message.text else ""
    await update.message.reply_text(f"Команда {command} получена, но пока не реализована.")

async def start_scheduler():
    hour, minute = map(int, SEND_TIME.split(':'))
    
    # Задача отправки сообщения в канал
    scheduler.add_job(
        check_and_send_message,
        trigger=CronTrigger(hour=hour, minute=minute),
        id='daily_game_message',
        name='Ежедневное сообщение об игре',
        replace_existing=True
    )
    
    # Задача отправки вопроса о выходном за 3 часа до публикации
    question_hour = (hour - 3) % 24
    scheduler.add_job(
        ask_about_vacation,
        trigger=CronTrigger(hour=question_hour, minute=minute),
        id='daily_vacation_question',
        name='Вопрос о выходном',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Планировщик запущен. Время отправки: {SEND_TIME}, время вопроса: {question_hour:02d}:{minute:02d}")

async def main():
    global application, bot
    
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.error("Не заданы BOT_TOKEN или CHANNEL_ID")
        return
    
    logger.info("Запуск бота...")
    
    # Создаем Application для обработки обновлений
    application = Application.builder().token(BOT_TOKEN).build()
    bot = application.bot
    
    # Регистрируем обработчики
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(CommandHandler("start", handle_command))
    application.add_handler(CommandHandler("help", handle_command))
    
    # Запускаем обработку обновлений
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Запускаем планировщик
    await start_scheduler()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
        scheduler.shutdown()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
