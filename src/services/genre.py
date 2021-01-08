from functools import lru_cache
from uuid import UUID
from typing import Optional, List
from collections import OrderedDict

from aioredis import Redis
from elasticsearch import AsyncElasticsearch
from fastapi import Depends


from db.elastic import get_elastic
from db.redis import get_redis
from cache.redis import RedisCache
from models.genre import Genre

DEFAULT_LIST_SIZE = 1000
GENRES_INDEX = 'genres'


def genres_keybuilder(genre_id: UUID) -> str:
    return f'genre:{str(genre_id)}'


class GenreService:
    def __init__(self, cache: RedisCache, elastic: AsyncElasticsearch):
        self.cache = cache
        self.elastic = elastic

    async def get_by_id(self, genre_id: UUID) -> Optional[Genre]:
        """
        Возвращает объект жанра. Он опционален, так как
        жанр может отсутствовать в базе
        """
        data = await self.cache.get(genre_id)
        if data:
            return Genre.parse_raw(data)

        docs = await self._es_get_by_ids([genre_id, ])
        if not docs:
            return None
        genre = Genre(**docs[0])
        await self.cache.put(genre.id, genre.json())

    async def list(self) -> List[Genre]:
        """
        Возвращает все жанры
        """
        # получаем только ID жанров
        genre_ids = await self._es_get_all()
        genres = OrderedDict.fromkeys(genre_ids, None)

        # проверяем есть ли полученные жанры в кеше по их ID
        for genre_id in genres.keys():
            data = await self.cache.get(genre_id)
            if data:
                genres[genre_id] = Genre.parse_raw(data)

        # не найденные в кеше жанры запрашиваем в эластике и кладём в кеш
        not_found = [genre_id for genre_id in genres.keys()
                     if genres[genre_id] is None]
        if not_found:
            docs = await self._es_get_by_ids(not_found)
            for doc in docs:
                genre = Genre(**doc)
                await self.cache.put(genre.id, genre.json())
                genres[genre.id] = genre
        return list(genres.values())

    async def _es_get_by_ids(self, genre_ids: List[UUID]) -> List[dict]:
        """
        Получает фильмы из elasticsearch по списку id
        """
        doc_ids = [{'_id': genre_id} for genre_id in genre_ids]
        resp = await self.elastic.mget(index=GENRES_INDEX, body={'docs': doc_ids})
        docs = [doc['_source'] for doc in resp['docs']]
        return docs

    async def _es_get_all(self) -> List[UUID]:
        """
        Возвращает список id фильмов из elasticsearch с учётом сортировки и фильтрации
        """
        params = {"_source": False, "size": DEFAULT_LIST_SIZE}
        docs = await self.elastic.search(index=GENRES_INDEX, params=params)
        ids = [UUID(doc['_id']) for doc in docs['hits']['hits']]
        return ids


@lru_cache()
def get_genre_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> GenreService:
    return GenreService(RedisCache(redis=redis,
                                   keybuilder=genres_keybuilder),
                        elastic)
