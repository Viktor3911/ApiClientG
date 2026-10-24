"""Настройки клиента из переменных окружения и файла .env в текущей папке.

Переменные окружения важнее значений из .env; аргументы клиента важнее обоих.
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

API_KEY_ENV = "G_API_KEY"
BASE_URL_ENV = "G_API_URL"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Ключ asg_... от администратора сервера.
    api_key: Optional[str] = Field(default=None, validation_alias=API_KEY_ENV)
    # Адрес сервера, например http://127.0.0.1:8000.
    base_url: Optional[str] = Field(default=None, validation_alias=BASE_URL_ENV)
