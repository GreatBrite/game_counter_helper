import os
from datetime import datetime

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

START_DATE = datetime(2025, 7, 13)
SEND_TIME = "12:00"

MESSAGE_TEMPLATE = "Коплю на BMW день {}"
