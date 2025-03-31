
from pydantic_settings import BaseSettings

"""Модуль настроек для загрузки конфигурации из .env файла с использованием pydantic-settings."""

class Settings(BaseSettings):
    """Класс для хранения настроек приложения с валидацией."""
    prod: bool  # Имя в нижнем регистре, мапится на PROD
    bot_token: str  # Мапится на BOT_TOKEN
    admin_user_nick: str  # Мапится на admin_user_nick
    db_lite: str  # Мапится на db_lite
    smtp_server: str  # Мапится на SMTP_SERVER
    port: int  # Мапится на PORT
    sender_email: str  # Мапится на sender_email
    sender_password: str  # Мапится на sender_password
    news_channel_url: str = "https://t.me/RepinNews"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "forbid"  # Запрещает лишние переменные
    }

settings = Settings()