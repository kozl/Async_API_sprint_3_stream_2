# Async API для сервиса фильмов

## Запуск приложения

1. Поднимаем elasticsearch, redis и приложение

```bash
docker-compose -f docker-compose.yaml -f docker-compose-backend.yaml up -d --build
```

2. Создаём схему схемы для индексов *movies*, *genres* и *persons*

```bash
./docker/es/create_es_schemas.sh
```

Приложение будет доступно на http://localhost:8888/
OpenAPI схема: http://localhost:8888/api/openapi


## Техническое задание

Предлагается выполнить проект «Асинхронное API». Этот сервис будет точкой входа для всех клиентов. В первой итерации в сервисе будут только анонимные пользователи. Функции авторизации и аутентификации запланированы в модуле «Auth».

<!-- vscode-markdown-toc -->
* 1. [Используемые технологии](#tech)
* 2. [Описание](#description)
* 3. [Основные сущности](#entites)
* 4. [Экраны в клиенском приложении](#screens)
	* 4.1. [Главная страница](#main)
	* 4.2. [Поиск](#search)
	* 4.3. [Страница фильма](#movie)
	* 4.4. [Страница персонажа](#person)
	* 4.5. [Страница жанра](#genre)
* 5. [Соответствие экранов и ендпоинтов](#endpoints)
	* 5.1. [Главная страница](#e-main)
	* 5.2. [Поиск](#e-search)
	* 5.3. [Страница фильма](#e-movie)
	* 5.4. [Страница персонажа](#e-person)
	* 5.5. [Страница жанра](#e-genre)
* 6. [Требования к проекту](#requirements)
* 7. [Требования к объёму данных](#data)

<!-- vscode-markdown-toc-config
	numbering=true
	autoSave=true
	/vscode-markdown-toc-config -->
<!-- /vscode-markdown-toc -->

###  1. <a name='tech'></a>Используемые технологии

- Код приложения пишется на **Python + FastAPI**.
- Приложение запускается под управлением сервера **ASGI**(uvicorn).
- Хранилище – **ElasticSearch**.
- За кеширование данных отвечает – **redis cluster**.
- Все компоненты системы запускаются через **docker**.

###  2. <a name='description'></a>Описание
В папке tasks ваша команда сможет найти задачи, которые необходимо выполнить в первом спринте второго модуля. Обратите внимание на задачи 00_create_repo и 01_create_basis – они являются блокирующими для командной работы, их необходимо выполнить как можно раньше.

Мы оценили задачи в story point'ах, значения которых брались из [последовательности Фибоначчи](https://ru.wikipedia.org/wiki/Числа_Фибоначчи) (1,2,3,5,8,…).
Вы можете разбить имеющиеся задачи на более маленькие – например, чтобы распределять между участниками команды не большие куски задания, а маленькие подзадачи. В таком случае не забудьте зафиксировать изменения в issues в репозитории.

**От каждого разработчика ожидается выполнение минимум 40% от общего числа story points в спринте.**

###  3. <a name='entites'></a>Основные сущности

- **Фильм** — заголовок, содержание, дата создания, возрастной ценз, режиссёры, актёры, сценаристы, жанры, ссылка на файл.
- **Сериал** — заголовок, содержание, даты создания, режиссёры, актёры, сценаристы, жанры, ссылка на файл.
- **Актёр** — имя, фамилия, фильмы с его участием.
- **Режиссёр** — имя, фамилия, фильмы, которые он снял.
- **Сценарист** — имя, фамилия, фильмы по его сценариям.
- **Жанр** — описание, популярность.

###  4. <a name='screens'></a>Экраны в клиенском приложении

####  4.1. <a name='main'></a>Главная страница

![Главная](https://pictures.s3.yandex.net/resources/00_welcome_content_images_S1_1_Practix_1603713438.jpg)

####  4.2. <a name='search'></a>Поиск

![Поиск](https://pictures.s3.yandex.net/resources/00_welcome_content_images_S1_2_Practix_1603713451.jpg)

####  4.3. <a name='movie'></a>Страница фильма

![Страница фильма](https://pictures.s3.yandex.net/resources/00_welcome_content_images_S1_3_Practix_1603713448.jpg)

####  4.4. <a name='person'></a>Страница персонажа

![Страница персонажа](https://pictures.s3.yandex.net/resources/00_welcome_content_images_S1_4_Practix_1603713455.jpg)

####  4.5. <a name='genre'></a>Страница жанра

![Страница жанра](https://pictures.s3.yandex.net/resources/00_welcome_content_images_S1_5_Practix_1603713452.jpg)

###  5. <a name='endpoints'></a>Соответствие экранов и ендпоинтов

####  5.1. <a name='e-main'></a>Главная страница

- На ней выводятся популярные фильмы. Пока у вас есть только один признак, который можно использовать в качестве критерия популярности — `imdb_rating`.

`/api/v1/film?sort=-imdb_rating`

```
http request
GET /api/v1/film?sort=-imdb_rating&page[size]=50&page[number]=1
[
{
  "uuid": "uuid",
  "title": "str",
  "imdb_rating": "float"
},
...
]

[
{
  "uuid": "524e4331-e14b-24d3-a156-426614174003",
  "title": "Ringo Rocket Star and His Song for Yuri Gagarin",
  "imdb_rating": 9.4
},
{
  "uuid": "524e4331-e14b-24d3-a156-426614174003",
  "title": "Lunar: The Silver Star",
  "imdb_rating": 9.2
},
...
]
```

- Жанр и популярные фильмы в нём. Просто фильтрация

`/api/v1/film?sort=-imdb_rating&filter[genre]=<comedy-uuid>`

```
http request
GET /api/v1/film?filter[genre]=<uuid:UUID>&sort=-imdb_rating&page[size]=50&page[number]=1
[
{
  "uuid": "uuid",
  "title": "str",
  "imdb_rating": "float"
},
...
]

[
{
  "uuid": "524e4331-e14b-24d3-a156-426614174003",
  "title": "Ringo Rocket Star and His Song for Yuri Gagarin",
  "imdb_rating": 9.4
},
{
  "uuid": "524e4331-e14b-24d3-a156-426614174003",
  "title": "Lunar: The Silver Star",
  "imdb_rating": 9.2
},
...
]
```

- Список жанров

`/api/v1/genre/`

```
http request
GET /api/v1/genre/
[
{
  "uuid": "uuid",
  "name": "str",
  ...
},
...
]

[
{
  "uuid": "d007f2f8-4d45-4902-8ee0-067bae469161",
  "name": "Adventure",
  ...
},
{
  "uuid": "dc07f2f8-4d45-4902-8ee0-067bae469164",
  "name": "Fantasy",
  ...
},
...
]
```

Онлайн-кинотеатру выгодно показывать как можно больше разных фильмов. Они не должны повторяться между блоком «популярное» и блоком конкретного жанра. Причём внутри списка «популярных» фильмов важно, чтобы в нём были представители разных жанров — так получится покрыть все возможные интересы пользователя при первом заходе. Подумайте об этом, хоть это и вне скоупа.

####  5.2. <a name='e-search'></a>Поиск

- Поиск по фильмам

`/api/v1/film/search/`

```
  http request
GET /api/v1/film/search?query=captain&page[number]=1&page[size]=50
[
{
  "uuid": "uuid",
  "title": "str",
  "imdb_rating": "float"
},
...
]

[
{
  "uuid": "223e4317-e89b-22d3-f3b6-426614174000",
  "title": "Billion Star Hotel",
  "imdb_rating": 6.1
},
{
  "uuid": "524e4331-e14b-24d3-a456-426614174001",
  "title": "Wishes on a Falling Star",
  "imdb_rating": 8.5
},
...
]
```

- Поиск по персонам

`/api/v1/person/search/`

```
http request
GET /api/v1/person/search?query=captain&page[number]=1&page[size]=50
[
{
  "uuid": "uuid",
  "full_name": "str",
  "role": "str",
  "film_ids": ["uuid"]
},
...
]
[
  {
    "uuid": "724e5631-e14b-14e3-g556-888814284902",
    "full_name": "Captain Raju",
    "role": "actor",
    "film_ids": ["eb055946-4841-4b83-9c32-14bb1bde5de4", ...]
 },
]
```

####  5.3. <a name='e-movie'></a>Страница фильма

- Полная информация по фильму

` /api/v1/film/<uuid:UUID>/`

```
  http request
GET /api/v1/film/<uuid:UUID>/
{
"uuid": "uuid",
"title": "str",
"imdb_rating": "float",
"description": "str",
"genre": [
  { "uuid": "uuid", "name": "str" },
  ...
],
"actors": [
  {
    "uuid": "uuid",
    "full_name": "str"
  },
  ...
],
"writers": [
  {
    "uuid": "uuid",
    "full_name": "str"
  },
  ...
],
"directors": [
  {
    "uuid": "uuid",
    "full_name": "str"
  },
  ...
],
}

{
"uuid": "b31592e5-673d-46dc-a561-9446438aea0f",
"title": "Lunar: The Silver Star",
"imdb_rating": 9.2,
"description": "From the village of Burg, a teenager named Alex sets out to become the fabled guardian of the goddess Althena...the Dragonmaster. Along with his girlfriend Luna, and several friends they meet along the journey, they soon discover that the happy world of Lunar is on the verge of Armageddon. As Dragonmaster, Alex could save it. As a ruthless and powerful sorceror is about to play his hand, will Alex and company succeed in their quest before all is lost? And is his girlfriend Luna involved in these world shattering events? Play along and find out.",
"genre": [
  {"name": "Action", "uuid": "6f822a92-7b51-4753-8d00-ecfedf98a937"},
  {"name": "Adventure", "uuid": "00f74939-18b1-42e4-b541-b52f667d50d9"},
  {"name": "Comedy", "uuid": "7ac3cb3b-972d-4004-9e42-ff147ede7463"}
],
"actors": [
  {
    "uuid": "afbdbaca-04e2-44ca-8bef-da1ae4d84cdf",
    "full_name": "Ashley Parker Angel"
  },
  {
    "uuid": "3c08931f-6138-46d1-b179-1bd076b6a236",
    "full_name": "Rhonda Gibson"
  },
  ...
],
"writers": [
  {
    "uuid": "1bd9a00b-9596-49a3-afbe-f39a632a09a9",
    "full_name": "Toshio Akashi"
  },
  {
    "uuid": "27fc3dc6-2656-43cb-8e56-d0dfb75ea0b2",
    "full_name": "Takashi Hino"
  },
  ...
],
"directors": [
  {
    "uuid": "4a893a97-e713-4936-9dd4-c8ca437ab483",
    "full_name": "Toshio Akashi"
  },
  ...
],
}
```

- Похожие фильмы. Похожесть можно оценить с помощью ElasticSearch, но цель модуля не в этом. Сделаем просто: покажем фильмы того же жанра.

`/api/v1/film?...`

####  5.4. <a name='e-person'></a>Страница персонажа

- Данные о персона

`/api/v1/person/<uuid:UUID>/`

```
  http request
GET /api/v1/person/<uuid:UUID>
{
"uuid": "uuid",
"full_name": "str",
"role": "str",
"film_ids": ["uuid"]
}

{
"uuid": "524e4331-e14b-24d3-a456-426614174002",
"full_name": "George Lucas",
"role": "writer",
"film_ids": ["uuid", ...]
}
```

- Фильмы по персоне

`/api/v1/person/<uuid:UUID>/film/`

```
http request
!DEPRECATED - used for old android devices

GET /api/v1/person/<uuid:UUID>/film
[
{
  "uuid": "uuid",
  "title": "str",
  "imdb_rating": "float"
},
...
]

[
{
  "uuid": "524e4331-e14b-24d3-a456-426614174001",
  "title": "Star Wars: Episode VI - Return of the Jedi",
  "imdb_rating": 8.3
},
{
  "uuid": "123e4317-e89b-22d3-f3b6-426614174001",
  "title": "Star Wars: Episode VII - The Force Awakens",
  "imdb_rating": 7.9
},
...
]
```

####  5.5. <a name='e-genre'></a>Страница жанра

- Данные по конкретному жанру

`/api/v1/genre/<uuid:UUID>/`

```
http request
GET /api/v1/genre/<uuid:UUID>
{
"uuid": "uuid",
"name": "str",
...
}

{
"uuid": "aabbd3f3-f656-4fea-9146-63f285edf5с1",
"name": "Action",
...
}
```

- Популярные фильмы в жанре

`/api/v1/film...`

###  6. <a name='requirements'></a>Требования к проекту

1. Структура API должна быть понятна пользователям и задокументирована.
2. Код проекта должен быть аккуратным и без дублирования.
3. Время ответа сервиса не превышает 200 мс.
4. В сервисе решена проблема [10к соединений](https://ru.wikipedia.org/wiki/C10k).

###  7. <a name='data'></a>Требования к объёму данных

- 200 000+ фильмов
- 200 000+ сериалов
- 500+ жанров
