
## Для запуска нужен docker и docker-compose

Инструкция по установке для разных операционок:
https://docs.docker.com/engine/install/

```bash
docker --version
docker-compose --version
```


## Запуск приложения 

```bash
git clone https://github.com/mylittletraf/kcu
cd kcu

# Сборка и запуск в фоновом режиме (выпустит консоль)
docker-compose up -d

# Сборка и запуск (выведет логи, cmd+c остановит программу)
docker-compose up
```



Логи (+ сохраняются в папку ./logs):

```bash
# Все логи
docker-compose logs -f  

# Логи загрузчика фильмов
docker-compose logs -f kcu

# Логи загрузчика мультфильмов
docker-compose logs -f kcu-mult

# Просмотр последних 300 строк логов
docker-compose logs -f --tail 300 kcu
```


## Полезные команды 


### Остановка контейнеров: 

```bash
docker-compose down
docker-compose down kcu
docker-compose down kcu-mult
```

### Перезапуск контейнеров: 

Нужно при изменении соответствующих сервису настроек в .env или config файлов

```bash
docker-compose restart kcu
docker-compose restart kcu-mult
```

### Просмотр запущенных сервисов

```bash
docker compose ps
```

### Запуск команд внутри контейнера: 

```bash
docker-compose exec kcu bash
docker-compose exec kcu-mult bash
```


## Удаление всех контейнеров, томов и сетей, созданных docker-compose:

```bash
docker-compose down -v --remove-orphans
```


## docker-compose файл


```
version: "3.8"  
services:  
  torapi:  
    image: lifailon/torapi:latest  
    container_name: TorAPI  
    environment:  
      - PORT=${PORT}  
      - PROXY_ADDRESS=${PROXY_ADDRESS}  
      - PROXY_PORT=${PROXY_PORT}  
      - USERNAME=${USERNAME}  
      - PASSWORD=${PASSWORD}  
    volumes:  
      - torapi:/rotapi  

#    Если нужно, чтобы был доступ к swagger извне, то
#    нужно расскоменить проброс портов
#    Ссылка http://ip-adress:8443/docs

#    ports:  
#      - "${PORT}:${PORT}"  
    restart: unless-stopped  
  kcu:  
    build:  
      context: ./kcu  
    command: poetry run python main.py  
    restart: unless-stopped  
    env_file:  
      - .env  
    environment:  
      - TZ=Europe/Moscow  
    volumes:  
      - ./result:/app/db  
      - ./logs:/app/logs  
      - ./config.json:/app/config.json  
    depends_on:  
      - torapi  
  kcu-mult:  
    build:  
      context: ./kcu  
    command: bash -c "sleep 60 && poetry run python main.py"  
    restart: unless-stopped  
    env_file:  
      - .env.mult  
    environment:  
      - TZ=Europe/Moscow  
    volumes:  
      - ./result:/app/db  
      - ./logs:/app/logs  
      - ./config-mult.json:/app/config.json  
    depends_on:  
      - torapi  
      - kcu  
volumes:  
  torapi:
```

## config.json + config-mult.json

```
{
 
  "GOOD_QUALITY": - список строк, теги которые мы считаем "хорошим качеством"
  "BAD_QUALITY": - список строк, теги которые мы считает "плохим качеством" и будет перезаливать 

  Списки строк с названиями категорий для российских фильмов в соответствующих трекерах  

  "RUSSIAN_CATEGORIES_RuTracker": [],
  "RUSSIAN_CATEGORIES_Kinozal": [],
  "RUSSIAN_CATEGORIES_NoNameClub": [],

  Списки строк с названиями категорий для зарубежных фильмов в соответствующих трекерах  
  
  "CATEGORIES_RuTracker": [],
  "CATEGORIES_Kinozal": [],
  "CATEGORIES_NoNameClub": []
}
```

## .env + .env.mult (описание полей продублированы в .env-example)

```

# Этот блок не трогаем!

PORT=8443  
PROXY_ADDRESS=  
PROXY_PORT=  
USERNAME=  
PASSWORD=  
URL_TORRAPI=http://torapi:8443  
CONFIG_FILE=config.json  
  
#===========================================  
#Все что ниже можно менять по необходимости  
#===========================================  
  
#Имя приложения для логгера  
APP_NAME=kcu_films  
  
#Эта ссылка используется для получения фильмов и загрузки торрента на сайт  
URL=https://kinotam.org  
  
#Эта ссылка используется для получения sid из кук  
URL_ADMIN=https://kinotam.org/tm/ {сюда TM} /  
  
#Токен для получения SID  
TM={сюда TM}  
  
#Варианты: request или browser  
#Изначально был браузер, заходил по URL_ADMIN и получал куки  
#Потом узнал про API и переделал на более легкий вариант  
#Не стал удалять опцию с браузером, мало-ли пригодится  
AUTH_METHOD=request  
  
#Фильмы старше этого года будут игнорироваться  
MIN_YEAR=1950  
  
#Для телеги  
TG_CHAT_ID=  
TG_USER_ID=  
TG_BOT_TOKEN=  
  
#Параметры для запроса получения фильмов на kinotam (91 - кино, 104 - мультфильм)  
CAT_ID=91  
OFFSET=0  
LIMIT=30  
  
#Максимальный размер фильма в GB  
MAX_SIZE=8  
  
#Минимальное количество просмотров для загрузки  
MIN_VIEWS=50  
  
#Время между запросами на добавление в секундах  
ADD_TIME_SLEEP=420  
  
#Через сколько запускать повторный поиск, отсчет начинается после завершения последней обработки  
RESTART_TIME=420  
  
#Имя базы данных, сохраняется в папке result в корне приложения, при DEBUG=True добавляется суффикс _test  
DB_NAME=films  
TABLE_NAME_GOOD_QUALITY=films_uploaded  
TABLE_NAME_BAD_QUALITY=films_bad_quality  
  
#При значении True, результат сохраняет в файл result/result.json в корне приложения  
#При значении False, загружает на сервер  
DEBUG=true  
  
#Если по каким то причинам получили от Kinotam пустой список фильмов,  
#то делаем GET_FILMS_RETRIES попыток с паузой GET_FILMS_DELAY (секунды)  
GET_FILMS_RETRIES=3  
GET_FILMS_DELAY=2  
  
#Если по каким то причинам не удалось получить magnet ссылку от torapi сервиса,  
#то делаем GET_MAGNET_RETRIES попыток с паузой GET_MAGNET_DELAY (секунды)  
GET_MAGNET_RETRIES=3  
GET_MAGNET_DELAY=1.0
```