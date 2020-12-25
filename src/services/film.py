from functools import lru_cache
from typing import Optional, List

from aioredis import Redis
from elasticsearch import AsyncElasticsearch
from fastapi import Depends

from db.elastic import get_elastic
from db.redis import get_redis
from models.film import Film

FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут


class FilmService:
    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    # get_by_id возвращает объект фильма. Он опционален, так как фильм может отсутствовать в базе
    async def get_by_id(self, film_id: str) -> Optional[Film]:
        film = await self._film_from_cache(film_id)
        if not film:
            film = await self._get_film_from_elastic(film_id)
            if not film:
                return None
            await self._put_film_to_cache(film)

        return film

    # list возвращает все фильмы
    async def list(self) -> List[Film]:
        film_ids = await self._list_film_ids_from_elastic()
        not_found = []
        result = []
        for film_id in filmids:
            film = await self._film_from_cache(film_id)
            if not film:
                not_found.append(film_id)
            else:
                result.append(film)
        # не найденные в кеше фильмы запрашиваем в эластике и кладём в кеш
        if not_found:
            films = await self._get_films_from_elastic(not_found)
            for film in films:
                await self._put_film_to_cache(film)
                result.append(film)
        return result

    async def _get_films_from_elastic(self, film_ids: List[str]) -> List[Film]:
        doc_ids = [{'_id': film_id} for film_id in film_ids]
        resp = await self.elastic.mget(index='movies', body={'docs': doc_ids})
        films = [Film(**doc['_source']) for doc in resp['docs']]
        return films

    async def _get_film_from_elastic(self, film_id: str) -> Optional[Film]:
        doc = await self.elastic.search('movies', film_id)
        return Film(**doc['_source'])

    async def _list_film_ids_from_elastic(self) -> List[str]:
        docs = await self.elastic.get(index='movies', params={"_source": False, "size": 1000})
        ids = [doc['_id'] for doc in docs]
        return ids

    async def _film_from_cache(self, film_id: str) -> Optional[Film]:
        # Пытаемся получить данные о фильме из кеша, используя команду get
        # https://redis.io/commands/get
        data = await self.redis.get(film_id)
        if not data:
            return None

        # pydantic предоставляет удобное API для создания объекта моделей из json
        film = Film.parse_raw(data)
        return film

    async def _put_film_to_cache(self, film: Film):
        # Сохраняем данные о фильме, используя команду set
        # Выставляем время жизни кеша — 5 минут
        # https://redis.io/commands/set
        # pydantic позволяет сериализовать модель в json
        await self.redis.set(film.id, film.json(), expire=FILM_CACHE_EXPIRE_IN_SECONDS)


@lru_cache()
def get_film_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    return FilmService(redis, elastic)
