import re

from config.settings import settings
from db.db import Database
from config.log_config import logger


def parse_size(size_str: str):
    try:
        cleaned = size_str.replace('\xa0', ' ').strip()
        value, unit = cleaned.split()
        value = float(value)
        return value if unit.upper() == "GB" else value / 1024 if unit.upper() == "MB" else None
    except (ValueError, AttributeError):
        return None


def normalize_name_to_pattern(name: str) -> str:
    parts = re.split(r'([.:—\-])', name)
    pattern_parts = []
    for part in parts:
        if part in {'.', ':', '-', '—'}:
            pattern_parts.append(r'[:.\-—]?')
        else:
            part = part.strip()
            if part:
                pattern_parts.append(rf"\b{re.escape(part)}\b")
    return r'\s*'.join(pattern_parts)

def build_name_pattern(local_name: str, orig_name: str = None, year: str = None) -> re.Pattern:
    conditions = []

    if local_name:
        local_name_pattern = normalize_name_to_pattern(local_name)
        conditions.append(local_name_pattern)

    if orig_name:
        conditions.append(rf"\b{re.escape(orig_name)}\b")

    if year:
        conditions.append(rf"\b{re.escape(str(year))}\b")

    pattern = ''.join(f"(?=.*{cond})" for cond in conditions) + ".*"
    return re.compile(pattern, re.IGNORECASE)


def filter_releases(app_settings: settings, raw_result, local_name, orig_name, year):
    result = []
    for tracker, items in raw_result.items():
        if not isinstance(items, list):
            continue

        for item in items:
            if item == "Result":
                continue
            item["tracker"] = tracker

        categories_key = f"RUSSIAN_CATEGORIES_{tracker}" if orig_name is None else f"CATEGORIES_{tracker}"
        categories = app_settings.get(categories_key)

        if not categories:
            continue

        name_pattern = build_name_pattern(local_name, orig_name, year)

        filtered_items = [
            item for item in items
            if item.get("Category") in categories
               and name_pattern.search(item.get("Name", ""))
               and (size_gb := parse_size(item.get("Size", ""))) is not None
               and size_gb < app_settings.max_size
        ]
        result.extend(filtered_items)

    return result or None


def filter_best_quality(app_settings: settings, items, film, update=False):
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

    good_items = find_items_by_tags(items, app_settings.get("GOOD_QUALITY", []))


    if update:
        if good_items:
            logger.info(f"Найдено более хорошее качество для фильма: {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
            Database.delete_film_by_id(film.get('id'), app_settings.table_bad_quality)
            logger.info(f"Удаление из 'films_bad_quality': {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
            Database.save_film(film, app_settings.table_good_quality)
            logger.info(f"Новая версия фильма на загрузку: {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
            min_priority = min(item["Priority"] for item in good_items)
            return [item for item in good_items if item["Priority"] == min_priority]
        else:
            return []

    if good_items:
        Database.save_film(film, app_settings.table_good_quality)
        logger.info(f"Фильм на загрузку: {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
        min_priority = min(item["Priority"] for item in good_items)
        return [item for item in good_items if item["Priority"] == min_priority]

    bad_items = find_items_by_tags(items, app_settings.get("BAD_QUALITY", []))
    if bad_items:
        logger.info(f"Плохое качество найдено для фильма: {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
        Database.save_film(film, app_settings.table_bad_quality)
        min_priority = min(item["Priority"] for item in bad_items)
        return [item for item in bad_items if item["Priority"] == min_priority]

    return []


def seed_count_filter(items):
    if not items:
        return None

    def safe_int(value):
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    return max(items, key=lambda x: safe_int(x.get('Seeds')))
