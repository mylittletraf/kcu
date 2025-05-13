import sqlite3

from log_config import logger
from settings import settings


class Database:
    """
    Класс для соединения с БД
    """
    db_filename = settings.db_name + '_test' if settings.debug else settings.db_name
    DB_NAME = f"./db/{db_filename}.db"

    logger.info(f"Подключаюсь к {DB_NAME}")

    @classmethod
    def connect(cls):
        return sqlite3.connect(cls.DB_NAME)

    @classmethod
    def init(cls):
        with cls.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {settings.table_bad_quality} (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    name_orig TEXT,
                    year INTEGER
                )
            ''')
            cursor.execute(f'''
               CREATE TABLE IF NOT EXISTS {settings.table_good_quality} (
                   id        INTEGER PRIMARY KEY,
                   name      TEXT NOT NULL,
                   name_orig TEXT,
                   year      INTEGER
               )
               ''')


    @classmethod
    def save_film(cls, film, table_name):
        with cls.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                INSERT OR IGNORE INTO {table_name} (id, name, name_orig, year)
                VALUES (?, ?, ?, ?)
            ''', (film['id'], film['name'], film.get('name_orig'), film.get('year')))

    @classmethod
    def get_all_films(cls, table_name):
        with cls.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT id, name, name_orig, year FROM {table_name}')
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
