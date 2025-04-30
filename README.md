
## Для запуска нужен docker

```bash
docker --version
docker-compose --version
```


## Запуск приложения 

```bash
git clone https://github.com/mylittletraf/kcu
cd kcu
```


Запуск в фоне:
```bash
docker-compose up -d
```


Логи (+ сохраняются в папку ./logs):

```bash
docker-compose logs -f
```


## Полезные команды 


### Остановка контейнеров: 

```bash
docker-compose down
```

### Перезапуск контейнеров: 

```bash
docker-compose restart
```

### Просмотр запущенных сервисов

```bash
docker compose ps
```

### Перезапуск отдельного сервиса: 

```bash
docker-compose restart имя_сервиса
```

### Просмотр логов одного сервиса: 

```bash
docker-compose logs имя_сервиса
```

### Запуск команд внутри контейнера: 

```bash
docker-compose exec имя_сервиса bash
```


## Удаление всех контейнеров, томов и сетей, созданных docker-compose:

```bash
docker-compose down -v --remove-orphans
```


## config.json

```
{
  "MAX_SIZE" - число, максимальный размер релиза в GB
  
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

## .env (описание полей продублированны в .env-example)

```
# Этот блок не трогаем!
===
PORT=8443
PROXY_ADDRESS=
PROXY_PORT=
USERNAME=
PASSWORD=
URL_TORRAPI=http://torapi:8443
====

# Далее ставим нужные значения

#Эта ссылка используется для получения фильмов и загрузки торрента на сайт
URL=

#Эта ссылка используется для получения sid из кук
URL_ADMIN=

#Токен для получения SID
TM=

#Варианты: request или browser
#Изначально был silenium, заходил по URL_ADMIN и получал куки
#Потом узнал про API и переделал на более легкий вариант
#Не стал удалять опцию с браузером, мало-ли пригодится
AUTH_METHOD=

#Фильмы старше этого года будут игнорироваться (костыль для момента, когда будем заливать только новинки)
MIN_YEAR=1950

#Для телеги
TG_CHAT_ID=
TG_USER_ID=
TG_BOT_TOKEN=

#Параметры для запроса получения фильмов на kinotam
CAT_ID=91
OFFSET=0
LIMIT=10

#Время между запросами на добавление в секундах
ADD_TIME_SLEEP=420

#Через сколько запускать повторный поиск, отсчет начинается после завершения последней обработки
RESTART_TIME=420

#Имя базы данных, сохраняется в папке result в корне приложения, при DEBUG=True добавляется суффикс _test
DB_NAME=films

#При значении True, результат сохраняет в файл result/result.json в корне приложения
#При значении False, загружает на сервер
DEBUG=true

#Если по каким то причинам получили от Kinotam пустой список фильмов,
#то делаем GET_FILMS_RETRIES попыток с паузой GET_FILMS_DELAY (секунды)
GET_FILMS_RETRIES=3
GET_FILMS_DELAY=2

```