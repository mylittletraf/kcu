import json
import asyncio

import httpx

from api_torrent import search_by_name, get_magnet_link
from db import Database
from filters import filter_releases, filter_best_quality, seed_count_filter
from kinotam import Kinotam

from log_config import logger
from settings import settings

async def process_film(app_settings: settings, client, film, uploaded_ids, update_mode=False):
    kinotam_id = film.get('id')
    name_local = film.get('name')
    name_orig = film.get('name_orig')
    year = (film.get('year'))
    views = int(film.get("views_cnt", 0))

    if not update_mode and views < app_settings.min_views:
        logger.info(
            f"Фильм {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')}) имеет меньше {app_settings.min_views} просмотров ({film.get('views_cnt')}), пропускаем")
        return None

    if not update_mode and kinotam_id in uploaded_ids:
        logger.info(f"Фильм {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')}) уже залит, пропускаем")
        return None

    full_name = " / ".join(str(part) for part in (name_local, name_orig, year) if part)
    full_name_to_upload = " | ".join(str(part) for part in (name_local, name_orig, year) if part)

    search_result = await search_by_name(app_settings, client, full_name)
    required_filtered = filter_releases(app_settings, search_result, name_local, name_orig, year)

    if not required_filtered:
        logger.info(f"Не найдено подходящих релизов для фильма {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
        return None

    if update_mode:
        best_item = filter_best_quality(app_settings, required_filtered, film, update=True)
        if not best_item:
            logger.info(f"Обновлений не найдено для фильма {film.get('name')} (id: {film.get('id')}, en: {film.get('name_orig')}, year: {film.get('year')})")
            return None
    else:
        best_item = filter_best_quality(app_settings, required_filtered, film)

    best_item = seed_count_filter(best_item)
    magnet_link = await get_magnet_link(app_settings, client, best_item["tracker"], best_item["Id"])

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

        kinotam_api = Kinotam(settings)

        films = kinotam_api.get_films_to_process(settings.get_film_retries, settings.get_film_delay)
        films_uploaded = Database.get_all_films(settings.table_good_quality)
        films_to_update = Database.get_all_films(settings.table_bad_quality)

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
                await asyncio.sleep(settings.time_sleep)
        else:
            with open(f"./db/result_{settings.app_name}.json", "w", encoding="utf-8") as f:
                logger.info(f"Сохраняю результат в json (DEBUG={settings.debug})")
                json.dump(final_result, f, ensure_ascii=False, indent=2)
        logger.info(f"Закончил работу, следующий запуск через {settings.restart_time / 60} минут")
        await asyncio.sleep(settings.restart_time)

if __name__ == '__main__':
    asyncio.run(main())