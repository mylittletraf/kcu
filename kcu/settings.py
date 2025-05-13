import json

from decouple import config


class Settings:
    def __init__(self):
        self.app_name = config("APP_NAME")
        self.url_admin = config("URL_ADMIN")
        self.url = config("URL")
        self.tm = config("TM")
        self.auth_method = config("AUTH_METHOD")
        self.url_torrent = config("URL_TORRAPI")
        self.cat_id = int(config("CAT_ID"))
        self.offset = int(config("OFFSET"))
        self.limit = int(config("LIMIT"))
        self.config_file = config("CONFIG_FILE")
        self.config_data = self._load_config()
        self.tg_chat_id = config("TG_CHAT_ID")
        self.tg_user_id = config("TG_USER_ID")
        self.tg_token = config("TG_BOT_TOKEN")
        self.db_name = config("DB_NAME")
        self.debug = config("DEBUG", default=True, cast=bool)
        self.time_sleep = int(config("ADD_TIME_SLEEP"))
        self.restart_time = int(config("RESTART_TIME"))
        self.get_film_retries = (int(config("GET_FILMS_RETRIES")))
        self.get_film_delay = int(config("GET_FILMS_DELAY"))
        self.max_size = int(config("MAX_SIZE"))
        self.table_bad_quality = config("TABLE_NAME_BAD_QUALITY")
        self.table_good_quality = config("TABLE_NAME_GOOD_QUALITY")
        self.min_views = int(config("MIN_VIEWS"))


    def _load_config(self):
        with open(self.config_file, encoding='utf-8') as f:
            return json.load(f)

    def get(self, key, default=None):
        return self.config_data.get(key, default)

settings = Settings()