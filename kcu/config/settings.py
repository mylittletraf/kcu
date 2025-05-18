import json
import os
from pathlib import Path
from typing import Dict, Any

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_base_path() -> Path:
    """
    Определяет базовый путь проекта, который используется для поиска файлов конфигурации.

    - В Docker: обычно /app
    - При локальном запуске: директория, содержащая модуль settings.py
    """
    # Проверяем переменную окружения для явного указания BASE_PATH
    env_base_path = os.environ.get("KCU_BASE_PATH")
    if env_base_path:
        return Path(env_base_path)

    # Проверяем наличие директории /app для Docker
    docker_path = Path("/app")
    if docker_path.exists():
        return docker_path

    # Для локального запуска используем директорию модуля
    module_dir = Path(os.path.dirname(os.path.abspath(__file__)))

    # Обычно код находится в kcu/, так что поднимаемся на уровень выше для получения корня проекта
    project_root = module_dir.parent
    return project_root


# Базовый путь проекта
BASE_PATH = get_base_path()


class Settings(BaseSettings):
    app_name: str
    url_admin: str
    url: str
    tm: str
    auth_method: str
    url_torrent: str
    cat_id: int
    max_limit: int
    limit: int
    config_file: str
    tg_chat_id: str = ""
    tg_user_id: str = ""
    tg_token: str = ""
    db_name: str
    debug: bool = True
    time_sleep: int
    restart_time: int
    get_film_retries: int
    get_film_delay: int
    get_magnet_retries: int
    get_magnet_delay: float
    max_size: int
    table_bad_quality: str
    table_good_quality: str
    min_views: int

    # Приватное поле для хранения данных из конфиг-файла
    _config_data: Dict[str, Any] = {}

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_PATH, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **data):
        super().__init__(**data)
        # Загружаем данные из config_file при инициализации, как в оригинале
        self._config_data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Метод для загрузки данных из конфигурационного файла."""
        try:
            with open(self.config_file, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка при загрузке конфигурационного файла: {e}")
            return {}

    def get(self, key, default=None):
        """
        Получение значения из конфигурационных данных.
        Сохраняет точно такой же интерфейс, как в оригинале.
        """
        return self._config_data.get(key, default)


# Создание экземпляра настроек
settings = Settings()
