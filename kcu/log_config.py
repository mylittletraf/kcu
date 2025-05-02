import logging
from logging.handlers import TimedRotatingFileHandler
import os
from settings import settings

os.makedirs("./logs", exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

file_handler = TimedRotatingFileHandler(
    filename="./logs/app.log",
    when="midnight",
    interval=1,
    backupCount=365,
    encoding='utf-8',
    utc=False
)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

if root_logger.hasHandlers():
    root_logger.handlers.clear()

root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(f"{settings.app_name}")
