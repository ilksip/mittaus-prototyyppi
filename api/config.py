import logging
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo


class Config:
    # Database access
    DB_USER = os.getenv("POSTGRES_USER", "app_db")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "app_password")
    DB_HOST = os.getenv("POSTGRES_HOST", "db")
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME = os.getenv("POSTGRES_DB", "db")
    # Mail service
    MAIL_SERVICE_ENABLED = os.getenv("MAIL_SERVICE_ENABLED", "false").lower() in ("true", "1", "t")
    SMTP_HOST= os.getenv("SMTP_HOST")
    SMTP_PORT= os.getenv("SMTP_PORT")
    SMTP_USER= os.getenv("SMTP_USER")
    SMTP_PASS= os.getenv("SMTP_PASS")
    # Misc settings
    LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() in ("true", "1", "t")
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "/app/logs/api.log")
    DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "t")
    TZ_STR = os.getenv("APP_TIMEZONE", "UTC")
    TZ_INFO = ZoneInfo(TZ_STR)
    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Config()

def setup_app_logging():
    if settings.DEBUG:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [
        logging.StreamHandler(sys.stdout) # Always print to console
    ]

    if settings.LOG_TO_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers
    )
    def custom_time_converter(*args):
        dt = datetime.now(settings.TZ_INFO)
        return dt.timetuple()

    logging.Formatter.converter = custom_time_converter

def format_timestamp(dt_from_db):
    local_dt = dt_from_db.astimezone(settings.TZ_INFO)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")

