import re
from functools import lru_cache
from typing import Optional, List
from uuid import UUID
from enum import Enum

from aioredis import Redis
from elasticsearch import AsyncElasticsearch
from pydantic import BaseModel
from starlette.datastructures import QueryParams
from fastapi import Depends


from db.elastic import get_elastic
from db.redis import get_redis
from cache.redis import RedisCache
from models.film import Film

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
        Парсит параметр, переданный в query и возвращает SortBy.
        По-умолчанию сортирует по рейтингу в порядке убывания.
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
        Парсит набор query параметров и возвращает FilterBy либо None.
        """
        for k, v in query.items():
            if k.startswith('filter'):
                match = re.match('filter\[(.+)\]', k)  # noqa: W605
                if match:
                    return cls.construct(attr=match[1], value=v)
        return None


def films_keybuilder(film_id: UUID) -> str:
    return f'film:{str(film_id)}'


def _build_filter_query(filter_by: FilterBy) -> dict:
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

    def __init__(self, cache: RedisCache, elastic: AsyncElasticsearch):
        self.cache = cache
        self.elastic = elastic

    async def get_by_id(self, film_id: UUID) -> Optional[Film]:
        """
        Возвращает объект фильма. Он опционален, так как
        фильм может отсутствовать в базе
        """
        data = await self.cache.get(film_id)
        if data:
            return Film.parse_raw(data)

        docs = await self._es_get_by_ids([film_id, ])
        if not docs:
            return None
        film = Film(**docs[0])
        await self.cache.put(film.id, film.json())

        return film

    async def list(self,
                   sort_by: Optional[SortBy] = None,
                   filter_by: Optional[FilterBy] = None) -> List[Film]:
        """
        Возвращает все фильмы
        """
        film_ids = await self._es_get_all(sort_by, filter_by)
        not_found = []
        result = []
        for film_id in film_ids:
            data = await self.cache.get(film_id)
            if not data:
                not_found.append(film_id)
            else:
                result.append(Film.parse_raw(data))
        # не найденные в кеше фильмы запрашиваем в эластике и кладём в кеш
        if not_found:
            docs = await self._es_get_by_ids(not_found)
            for doc in docs:
                film = Film(**doc)
                await self.cache.put(film.id, film.json())
                result.append(film)
        return result

    async def _es_get_by_ids(self, film_ids: List[UUID]) -> List[dict]:
        """
        Получает фильмы из elasticsearch по списку id
        """
        doc_ids = [{'_id': film_id} for film_id in film_ids]
        resp = await self.elastic.mget(index='movies', body={'docs': doc_ids})
        docs = [doc['_source'] for doc in resp['docs']]
        return docs

    async def _es_get_all(self,
                          sort_by: Optional[SortBy] = None,
                          filter_by: Optional[FilterBy] = None) -> List[UUID]:
        """
        Возвращает список id фильмов из elasticsearch с учётом сортировки и фильтрации
        """
        params = {"_source": False, "size": DEFAULT_LIST_SIZE}
        if sort_by:
            params.update({'sort': f'{sort_by.attr}:{sort_by.order.value}'})
        body = None
        if filter_by:
            body = _build_filter_query(filter_by)
        docs = await self.elastic.search(index='movies', params=params, body=body)
        ids = [UUID(doc['_id']) for doc in docs['hits']['hits']]
        return ids


@lru_cache()
def get_film_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    return FilmService(RedisCache(redis=redis,
                                  keybuilder=films_keybuilder),
                       elastic)
