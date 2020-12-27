## Запуск Elasticsearch и redis

1. Поднимаем elasticsearch и redis
```docker-compose up -d --build```
2. Для создания схемы индекса _movies_ вызываем команду из /docker/es/es_schema_movies.txt

## Запуск python Backend
1. Создаем образ нашего backend
```docker build -t python-api-backend .```
2. Запускаем приложение
```docker run --rm --network async_api_sprint_3_stream_2_default -p 8888:8888 --name=python-api-backend python-api-backend```
* Здесь указываем _network_ = _async_api_sprint_3_stream_2_default_ , чтобы обращаться к elasticsearch и redis по названию контейнеров.
* _async_api_sprint_3_stream_2_default_ создается автоматически после запуска elasticsearch и redis.
* Аргументом _-p_ пробрасываем порт на локальную машину
* Приложение будет доступно на http://localhost:8888/
