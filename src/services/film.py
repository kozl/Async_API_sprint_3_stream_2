import re
from functools import lru_cache
from typing import Optional, List
from uuid import UUID
from enum import Enum
from collections import defaultdict

from aioredis import Redis
from elasticsearch import AsyncElasticsearch
from pydantic import BaseModel
from starlette.datastructures import QueryParams
from fastapi import Depends


from db.elastic import get_elastic
from db.redis import get_redis
from models.film import Film

FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут
DEFAULT_LIST_SIZE = 1000


class SortOrder(Enum):
    ASC = 'asc'
    DESC = 'desc'


class FilterByAttr(Enum):
    GENRE = 'genre'
    ACTOR = 'actor'
    DIRECTOR = 'director'
    WRITER = 'writer'


class SortBy(BaseModel):
    attr: str
    order: SortOrder

    @classmethod
    def from_param(cls, param: Optional[str]):
        """
        Парсит параметр, переданный в query и возвращает SortBy
        """
        if param is None:
            return cls.construct(attr='imdb_rating', order=SortOrder.DESC)
        order = SortOrder.DESC
        if param.startswith('+'):
            order = SortOrder.ASC
        return cls.construct(attr=param[1:], order=order)


class FilterBy(BaseModel):
    attr: FilterByAttr
    value: str

    @classmethod
    def from_query(cls, query: QueryParams):
        """
        Парсит набор query параметров и возвращает FilterBy
        """
        for k, v in query.items():
            if k.startswith('filter'):
                m = re.match('filter\[(.+)\]', k)
                if m is None:
                    continue
                return cls.construct(attr=m[1], value=v)
        return None


def _build_query(filter_by: FilterBy) -> dict:
    """
    Формирует поисковый запрос для фильтрации по аттрибутам фильма
    """
    path = 'actors'
    if filter_by.attr == FilterByAttr.GENRE.value:
        path = 'genres'
    elif filter_by.attr == FilterByAttr.ACTOR.value:
        path = 'actors'
    elif filter_by.attr == FilterByAttr.DIRECTOR.value:
        path = 'directors'
    elif filter_by.attr == FilterByAttr.WRITER.value:
        path = 'writers'
    return {
        'query': {
            'nested': {
                'path': path,
                'query': {
                    'match': {f'{path}.id': filter_by.value}
                }
            }
        }
    }


class FilmService:

    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_by_id(self, film_id: UUID) -> Optional[Film]:
        """
        Возвращает объект фильма. Он опционален, так как фильм может отсутствовать в базе
        """
        film = await self._film_from_cache(film_id)
        if not film:
            film = await self._get_film_from_elastic(film_id)
            if not film:
                return None
            await self._put_film_to_cache(film)

        return film

    async def list(self, sort_by: Optional[SortBy] = None, filter_by: Optional[FilterBy] = None) -> List[Film]:
        """
        Возвращает все фильмы
        """
        film_ids = await self._list_film_ids_from_elastic(sort_by, filter_by)
        not_found = []
        result = []
        for film_id in film_ids:
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

    async def _get_films_from_elastic(self, film_ids: List[UUID]) -> List[Film]:
        """
        Получает фильмы из elasticsearch по списку id
        """
        doc_ids = [{'_id': film_id} for film_id in film_ids]
        resp = await self.elastic.mget(index='movies', body={'docs': doc_ids})
        films = [Film(**doc['_source']) for doc in resp['docs']]
        return films

    async def _get_film_from_elastic(self, film_id: UUID) -> Optional[Film]:
        """
        Получает фильм из elasticsearch по id
        """
        doc = await self.elastic.get('movies', film_id)
        return Film(**doc['_source'])

    async def _list_film_ids_from_elastic(self, sort_by: Optional[SortBy] = None, filter_by: Optional[FilterBy] = None) -> List[UUID]:
        """
        Возвращает список id фильмов из elasticsearch с учётом сортировки и фильтрации
        """
        params = {"_source": False, "size": DEFAULT_LIST_SIZE}
        if sort_by:
            params.update({'sort': f'{sort_by.attr}:{sort_by.order.value}'})
        body = None
        if filter_by:
            body = _build_query(filter_by)
        docs = await self.elastic.search(index='movies', params=params, body=body)
        ids = [doc['_id'] for doc in docs['hits']['hits']]
        return ids

    async def _film_from_cache(self, film_id: UUID) -> Optional[Film]:
        """
        Отдаёт фильм из кеша по id
        """
        data = await self.redis.get(str(film_id))
        if not data:
            return None

        film = Film.parse_raw(data)
        return film

    async def _put_film_to_cache(self, film: Film):
        """
        Сохраняет фильм в кеш
        """
        await self.redis.set(str(film.id), film.json(), expire=FILM_CACHE_EXPIRE_IN_SECONDS)


@lru_cache()
def get_film_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    return FilmService(redis, elastic)
