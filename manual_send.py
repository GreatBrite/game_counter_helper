import asyncio
from main import check_and_send_message

if __name__ == "__main__":
    print("Запуск ручной проверки и отправки сообщения...")
    asyncio.run(check_and_send_message())
    print("Готово!")
