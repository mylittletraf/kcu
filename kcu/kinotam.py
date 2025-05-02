import time

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from log_config import logger


class Kinotam:
    def __init__(self, url: str, url_admin: str, tm: str, auth_method:str, cat_id: int, offset: int, limit: int, tg_chat_id: str, tg_user_id: str, tg_token: str):
        self.url = url
        self.url_admin = url_admin
        self.tm = tm
        self.auth_method = auth_method
        self.cat_id = cat_id
        self.offset = offset
        self.limit = limit
        self.cookies = self.get_cookies()
        self.tg_chat_id = tg_chat_id
        self.tg_user_id = tg_user_id
        self.tg_token = tg_token

    def get_cookies(self, max_retries=3, delay=2):
        if self.auth_method == "browser":
            return self._get_cookies_with_browser()
        elif self.auth_method == "request":
            return self._get_cookies_with_request(max_retries, delay)
        else:
            logger.error(f"Неизвестный метод аутентификации: {self.auth_method}")
            return None

    def _get_cookies_with_browser(self):
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium import webdriver

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')

        logger.info("Инициализация браузера")
        driver = webdriver.Chrome(
            service=Service("/usr/bin/chromedriver"),
            options=options
        )

        try:
            logger.info(f"Перехожу по {self.url_admin[:37]}... ")
            driver.get(self.url_admin)
            selenium_cookies = driver.get_cookies()
            cookies_dict = {cookie['name']: cookie['value'] for cookie in selenium_cookies}
            logger.info(f"Успешно получил куки {cookies_dict}")
            return cookies_dict
        except Exception as e:
            logger.error(f"Ошибка при получении куков через браузер: {e}")
            return None
        finally:
            driver.quit()

    def _get_cookies_with_request(self, max_retries, delay):
        api_url = f"{self.url}/api/session/login/"
        data = {"tm": self.tm}
        cookies_dict = {"sandbox": "beta"}
        session = requests.Session()

        logger.info("Получаю sid через HTTP-запрос")

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Попытка {attempt}: отправка запроса на {api_url}")
                response = session.post(api_url, data=data)
                response.raise_for_status()
                json_response = response.json()
                sid = json_response.get('attributes', {}).get('sid')

                if sid:
                    logger.info(f"Получен sid: {sid}")
                    cookies_dict["sid"] = sid
                    logger.info(f"Установленные куки: {cookies_dict}")
                    return cookies_dict
                else:
                    logger.error(f"Не удалось получить sid: {json_response}")
                    return None

            except Exception as e:
                logger.warning(f"Ошибка при попытке {attempt}: {e}")
                time.sleep(delay)

        logger.error("Превышено максимальное число попыток получения sid")
        return None

    def get_films_to_process(self, max_retries=3, delay=2):
        api_url = self.url + '/api/films/upload/list/'
        session = requests.Session()
        session.cookies.update(self.cookies)

        data = {
            'Ot': self.cat_id,
            'O': self.offset,
            'L': self.limit,
            '_origin': self.url
        }

        for attempt in range(1, max_retries + 1):
            logger.info(f"Попытка {attempt}: Получаю фильмы на обработку")
            try:
                response = session.post(api_url, data=data)
                response.raise_for_status()

                json_response = response.json()
                items = json_response.get('items')

                if items:
                    logger.info(f"Фильмы на обработку: {items}")
                    return items
                else:
                    logger.warning(f"Список фильмов пустой (попытка {attempt})")
                    time.sleep(delay)

            except Exception as e:
                logger.warning(f"Ошибка при получении списка фильмов (попытка {attempt}): {e}")
                time.sleep(delay)

        logger.error("Не удалось получить список фильмов после всех попыток")
        return []

    def upload_film(self, film):

        data = {
            "Ot": self.cat_id,
            "Oi": film.get("id"),
            "title": film.get("name_to_api"),
            "torrent": film.get('magnet'),
        }

        api_url = self.url + '/api/films/upload/add/'
        session = requests.Session()
        session.cookies.update(self.cookies)
        logger.info(f"Добавляю фильм на сайт {film}")
        target_name = (
            "Фильм" if self.cat_id == 91
            else "Мультфильм" if self.cat_id == 104
            else ""
        )

        try:
            response = session.post(api_url, data=data)
            json_response = response.json()
            if json_response.get("code") == "00000":
                logger.info(f"Добавил {target_name}. {json_response}, ")
                self.send_message_tg(film, "✅ *Залил фильм:*")
            elif json_response.get("code") == "00037":
                logger.warning(f"Загружен дубль. {json_response}, ")
                self.send_message_tg(film, "⚠️ *Попытка повторной загрузки:*")
            else:
                logger.warning(f"Ошибка при загрузке {target_name.lower()}a. {json_response}, ")
                self.send_message_tg(film, f"⛔️ *Ошибка при загрузке {target_name.lower()}a ({json_response.get("code")}):*")

            return response

        except Exception as e:
            logger.warning(f"Ошибка при добавлении фильма")
            return 'Ошибка ', e

    def send_message_tg(self, film, message_status):
        url = f'https://api.telegram.org/bot{self.tg_token}/sendMessage'

        message = (
            f"{message_status}\n"
            f"\n"
            f"*Дата загрузки:* {datetime.now().strftime("%d.%m.%Y %H:%M")}\n"
            f"*ID:* `{film.get('id')}`\n"
            f"*Название:* `{film.get('name_to_api')}`\n"
            f"*Название раздачи:* `{film.get('name_release')}`\n"
            f"\n"
            f"[🔗 Фильм на Kinotam]({self.url}/movie/?Oi={film.get('id')})\n"
            f"[🔗 Ссылка на раздачу]({film.get('url')})\n"
        )

        payload = {
            'chat_id': self.tg_chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        logger.info(f"Отправка уведомления в telegram")
        requests.post(url, data=payload)

