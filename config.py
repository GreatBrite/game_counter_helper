import os
from datetime import datetime

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
BOSS_USERNAME = os.getenv('BOSS_USERNAME', 'gr8brite')
BOSS_CHAT_ID = os.getenv('BOSS_CHAT_ID')  # ID чата с боссом для отправки вопросов

START_DATE = datetime(2025, 11, 11)
SEND_TIME = "13:00"

MESSAGE_TEMPLATE = "Разрабатываю игру день {}"
VACATION_HASHTAG = "\n#выходной@greatbritedevelop"
