import asyncio
from typing import TypedDict

import httpx
from config.log_config import logger
from config.settings import settings


class SearchByNameResponse(TypedDict):
    Id: str
    Name: str
    Name_Original: str
    Year: int
    Tracker: str
    Size: int
    Seeders: int
    Leechers: int
    Magnet: str

async def search_by_name(
    app_settings: settings,
    client: httpx.AsyncClient,
    query,
    target="all",
) -> SearchByNameResponse:
    response = await client.get(
        f"{app_settings.url_torrent}/api/search/title/{target}",
        params={"query": query}
    )
    response.raise_for_status()
    return response.json()


async def get_magnet_link(
    app_settings: settings,
    client: httpx.AsyncClient,
    tracker: str,
    torrent_id: str,
) -> str | None:
    url = f"{app_settings.url_torrent}/api/search/id/{tracker.lower()}"
    params = {"query": torrent_id}
    retries = app_settings.get_magnet_retries
    delay = app_settings.get_magnet_delay

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
