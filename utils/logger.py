import os
from loguru import logger

# Ensure logs directory exists
if not os.path.exists("logs"):
    os.makedirs("logs")

# Configure loguru to match the user's requirements:
# - rotation="1 hour": Creates a new log file every hour.
# - retention="1 day": Deletes files older than 1 day (at the end of the day).
# - enqueue=True: Thread-safe logging.
logger.add(
    "logs/app_{time:YYYY-MM-DD_HH}.log",
    rotation="1 hour",
    retention="1 day",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{file}:{line} - {message}",
    level="INFO",
    enqueue=True,
    backtrace=False,
    diagnose=False
)
