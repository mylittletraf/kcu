import sqlite3
import os
from pathlib import Path

from config.log_config import logger
from config.settings import settings


class Database:
    """
    Класс для соединения с БД
    """
    db_filename = settings.db_name + '_test' if settings.debug else settings.db_name
    DB_DIR = "./db"
    DB_PATH = Path(f"{DB_DIR}/{db_filename}.db")

    @classmethod
    def ensure_db_dir_exists(cls):
        """Создает директорию для БД, если она не существует"""
        if not os.path.exists(cls.DB_DIR):
            logger.info(f"Создаю директорию для БД: {cls.DB_DIR}")
            os.makedirs(cls.DB_DIR, exist_ok=True)

    @classmethod
    def connect(cls):
        """Подключение к БД с предварительной проверкой существования директории"""
        cls.ensure_db_dir_exists()

        # Проверяем, существует ли файл БД
        db_exists = os.path.exists(cls.DB_PATH)
        if not db_exists:
            logger.info(f"Создаю новую базу данных: {cls.DB_PATH}")
        else:
            logger.info(f"Подключаюсь к существующей БД: {cls.DB_PATH}")

        return sqlite3.connect(cls.DB_PATH)

    @classmethod
    def init(cls):
        """Инициализация БД: создание таблиц, если они не существуют"""
        cls.ensure_db_dir_exists()

        with cls.connect() as conn:
            cursor = conn.cursor()

            # Создаем таблицу для фильмов плохого качества
            logger.info(
                f"Создаю таблицу {settings.table_bad_quality} (если не существует)")
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {settings.table_bad_quality} (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    name_orig TEXT,
                    year INTEGER
                )
            ''')

            # Создаем таблицу для фильмов хорошего качества
            logger.info(
                f"Создаю таблицу {settings.table_good_quality} (если не существует)")
            cursor.execute(f'''
               CREATE TABLE IF NOT EXISTS {settings.table_good_quality} (
                   id        INTEGER PRIMARY KEY,
                   name      TEXT NOT NULL,
                   name_orig TEXT,
                   year      INTEGER
               )
            ''')

            logger.info("Инициализация БД завершена")

    @classmethod
    def save_film(cls, film, table_name):
        with cls.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                INSERT OR IGNORE INTO {table_name} (id, name, name_orig, year)
                VALUES (?, ?, ?, ?)
            ''', (film['id'], film['name'], film.get('name_orig'),
                  film.get('year')))

    @classmethod
    def get_all_films(cls, table_name):
        with cls.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'SELECT id, name, name_orig, year FROM {table_name}')
            rows = cursor.fetchall()

            films = []
            for row in rows:
                film = {
                    "id": row[0],
                    "name": row[1],
                    "name_orig": row[2],
                    "year": row[3],
                }
                films.append(film)

            return films

    @classmethod
    def delete_film_by_id(cls, film_id, table_name):
        with cls.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {table_name} WHERE id = ?', (film_id,))
            conn.commit()
