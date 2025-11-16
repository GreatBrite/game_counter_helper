import os
from datetime import datetime

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

START_DATE = datetime(2025, 11, 11)
SEND_TIME = "12:00"

MESSAGE_TEMPLATE = "Разрабатываю игру день {}"
