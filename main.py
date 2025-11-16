import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Bot
from telegram.error import TelegramError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
load_dotenv()
from config import BOT_TOKEN, CHANNEL_ID, START_DATE, SEND_TIME, MESSAGE_TEMPLATE

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
scheduler = AsyncIOScheduler()

def calculate_day_number():
    today = datetime.now().date()
    start_date = START_DATE.date()
    delta = today - start_date
    return delta.days + 1

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
                    if "Коплю на BMW день" in message.text:
                        message_sent_today = True
                        logger.info("Найдено сообщение за сегодня - пропускаем отправку")
                        break
        
        if not message_sent_today:
            message_text = MESSAGE_TEMPLATE.format(current_day)
            await bot.send_message(chat_id=CHANNEL_ID, text=message_text)
            logger.info(f"Отправлено сообщение: {message_text}")
        else:
            logger.info("Сообщение уже было отправлено сегодня")
            
    except TelegramError as e:
        logger.error(f"Ошибка Telegram: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")

async def start_scheduler():
    hour, minute = map(int, SEND_TIME.split(':'))
    
    scheduler.add_job(
        check_and_send_message,
        trigger=CronTrigger(hour=hour, minute=minute),
        id='daily_bmw_message',
        name='Ежедневное сообщение о BMW',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Планировщик запущен. Время отправки: {SEND_TIME}")

async def main():
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.error("Не заданы BOT_TOKEN или CHANNEL_ID")
        return
    
    logger.info("Запуск бота...")
    await start_scheduler()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
        scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
