import re
import json
import sqlite3
import asyncio
import time
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional

import httpx
from decouple import AutoConfig

from kinotam import Kinotam

from log_config import logger
from settings import settings


BASE_DIR = Path(__file__).resolve().parent
config = AutoConfig(search_path=BASE_DIR)

class Database:

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


def parse_size(size_str):
    try:
        cleaned = size_str.replace('\xa0', ' ').strip()
        value, unit = cleaned.split()
        value = float(value)
        return value if unit.upper() == "GB" else value / 1024 if unit.upper() == "MB" else None
    except (ValueError, AttributeError):
        return None


async def search_by_name(settings, client, query, target="all"):
    response = await client.get(
        f"{settings.url_torrent}/api/search/title/{target}",
        params={"query": query}
    )
    response.raise_for_status()
    return response.json()




async def get_magnet_link(settings: settings, client: httpx.AsyncClient, tracker: str, torrent_id: str, retries: int = 3, delay: float = 1.0) -> Optional[str]:
    url = f"{settings.url_torrent}/api/search/id/{tracker.lower()}"
    params = {"query": torrent_id}

    for attempt in range(1, retries + 1):
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()

            if result and isinstance(result, list) and "Magnet" in result[0]:
                return result[0]["Magnet"]

            logger.warning(f"[Попытка {attempt}] Нет поля 'Magnet' в результате для tracker={tracker}, id={torrent_id}")

        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            logger.error(f"[Попытка {attempt}] Ошибка при получении magnet-ссылки: {e}")

        if attempt < retries:
            await asyncio.sleep(delay)

    logger.error(f"Не удалось получить magnet-ссылку после {retries} попыток: tracker={tracker}, id={torrent_id}")
    return None

def normalize_name_to_pattern(name: str) -> str:
    parts = re.split(r'([.:—\-])', name)
    pattern_parts = []
    for part in parts:
        if part in {'.', ':', '-', '—'}:
            pattern_parts.append(r'[:.\-—]?')
        else:
            pattern_parts.append(re.escape(part.strip()))
    return r'\s*'.join(pattern_parts)


def build_name_pattern(local_name: str, orig_name: str = None, year: str = None) -> re.Pattern:
    conditions = []

    if local_name:
        local_name_pattern = normalize_name_to_pattern(local_name)
        conditions.append(local_name_pattern)

    if orig_name:
        conditions.append(re.escape(orig_name))

    if year:
        conditions.append(re.escape(str(year)))

    pattern = ''.join(f"(?=.*{cond})" for cond in conditions) + ".*"
    return re.compile(pattern, re.IGNORECASE)



def filter_releases(settings, raw_result, local_name, orig_name, year):
    result = []
    for tracker, items in raw_result.items():
        if not isinstance(items, list):
            continue

        for item in items:
            if item == "Result":
                continue
            item["tracker"] = tracker

        categories_key = f"RUSSIAN_CATEGORIES_{tracker}" if orig_name is None else f"CATEGORIES_{tracker}"
        categories = settings.get(categories_key)

        if not categories:
            continue

        name_pattern = build_name_pattern(local_name, orig_name, year)

        filtered_items = [
            item for item in items
            if item.get("Category") in categories
            and name_pattern.search(item.get("Name", ""))
            and (size_gb := parse_size(item.get("Size", ""))) is not None
            and size_gb < settings.get("MAX_SIZE", 10)
        ]
        result.extend(filtered_items)

    return result or None


def filter_best_quality(settings, items, film, update=False):
    def find_items_by_tags(items, tags):
        tag_priority = {tag: idx for idx, tag in enumerate(tags)}
        matched = []
        for item in items:
            name = str(item.get("Name", ""))
            for tag in tags:
                pattern = re.escape(tag).replace(r"\ ", r"\s+")
                try:
                    if re.search(pattern, name, flags=re.IGNORECASE):
                        item["Tag"] = tag
                        item["Priority"] = tag_priority[tag]
                        matched.append(item)
                        break
                except Exception as e:
                    logger.warning(f"Ошибка при поиске по шаблону '{pattern}' в названии '{name}': {e}")
        return matched

    good_items = find_items_by_tags(items, settings.get("GOOD_QUALITY", []))


    if update:
        if good_items:
            logger.info(f"Найдено более хорошее качество для фильма: {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
            Database.delete_film_by_id(film.get('id'), "films_bad_quality")
            logger.info(f"Удаление из 'films_bad_quality': {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
            Database.save_film(film, "films_uploaded")
            logger.info(f"Новая версия фильма на загрузку: {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
            min_priority = min(item["Priority"] for item in good_items)
            return [item for item in good_items if item["Priority"] == min_priority]
        else:
            return []

    if good_items:
        Database.save_film(film, "films_uploaded")
        logger.info(f"Фильм на загрузку: {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
        min_priority = min(item["Priority"] for item in good_items)
        return [item for item in good_items if item["Priority"] == min_priority]

    bad_items = find_items_by_tags(items, settings.get("BAD_QUALITY", []))
    if bad_items:
        logger.info(f"Плохое качество найдено для фильма: {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
        Database.save_film(film, "films_bad_quality")
        min_priority = min(item["Priority"] for item in bad_items)
        return [item for item in bad_items if item["Priority"] == min_priority]

    return []


def seed_count_filter(items):
    return max(items, key=lambda x: int(x.get('Seeds', 0)))


async def process_film(settings, client, film, uploaded_ids, update_mode=False):
    kinotam_id = film.get('id')
    name_local = film.get('name')
    name_orig = film.get('name_orig')
    year = film.get('year')

    if not update_mode and kinotam_id in uploaded_ids:
        logger.info(f"Фильм {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')}) уже залит, пропускаем")
        return None

    full_name = " / ".join(str(part) for part in (name_local, name_orig, year) if part)
    full_name_to_upload = " | ".join(str(part) for part in (name_local, name_orig, year) if part)

    search_result = await search_by_name(settings, client, full_name)
    required_filtered = filter_releases(settings, search_result, name_local, name_orig, year)

    if not required_filtered:
        logger.info(f"Не найдено подходящих релизов для фильма {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
        return None

    if update_mode:
        best_item = filter_best_quality(settings, required_filtered, film, update=True)
        if not best_item:
            logger.info(f"Обновлений не найдено для фильма {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
            return None
    else:
        best_item = filter_best_quality(settings, required_filtered, film)

    best_item = seed_count_filter(best_item)
    magnet_link = await get_magnet_link(settings, client, best_item["tracker"], best_item["Id"])

    if not magnet_link:
        logger.warning(f"Не удалось получить magnet-ссылку для фильма {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
        return None

    return {
        "id": kinotam_id,
        "kinotam_name": full_name_to_upload,
        "name_release": best_item.get("Name"),
        "name_to_api": " | ".join(part for part in (full_name_to_upload, best_item.get('Tag')) if part),
        "url": best_item.get("Url"),
        "magnet": magnet_link
    }


async def main():
    Database.init()

    while True:

        kinotam_api = Kinotam(
            settings.url,
            settings.url_admin,
            settings.tm,
            settings.auth_method,
            settings.cat_id,
            settings.offset,
            settings.limit,
            settings.tg_chat_id,
            settings.tg_user_id,
            settings.tg_token
        )

        films = kinotam_api.get_films_to_process(settings.get_film_retries, settings.get_film_delay)
        films_uploaded = Database.get_all_films("films_uploaded")
        films_to_update = Database.get_all_films("films_bad_quality")

        uploaded_ids = {film['id'] for film in (films_uploaded + films_to_update)}

        final_result = []

        async with httpx.AsyncClient(timeout=20.0) as client:
            for film in films:
                result = await process_film(settings, client, film, uploaded_ids, update_mode=False)
                if result:
                    final_result.append(result)

            for film in films_to_update:
                logger.info(f"Проверяю фильм с плохим качеством на наличие обновлений {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
                result = await process_film(settings, client, film, uploaded_ids, update_mode=True)
                if result:
                    final_result.append(result)

        if not settings.debug:
            for film_to_upload in final_result:
                logger.info(f"Загружаю фильм [{film_to_upload.get('id')}] | {film_to_upload.get('name_to_api')}")
                kinotam_api.upload_film(film_to_upload)
                logger.info(f"Ждем {settings.time_sleep / 60} минут до следующей отправки")
                time.sleep(settings.time_sleep)
        else:
            with open(f"./db/result_{settings.app_name}.json", "w", encoding="utf-8") as f:
                logger.info(f"Сохраняю результат в json (DEBUG={settings.debug})")
                json.dump(final_result, f, ensure_ascii=False, indent=2)
        logger.info(f"Закончил работу, следующий запуск через {settings.restart_time / 60} минут")
        await asyncio.sleep(settings.restart_time)

if __name__ == '__main__':
    asyncio.run(main())