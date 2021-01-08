import re
from functools import lru_cache
from typing import Optional, List, Dict
from uuid import UUID
from enum import Enum
from collections import OrderedDict

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
FILMS_INDEX = 'movies'


class Roles(Enum):
    ACTOR = 'actors'
    DIRECTOR = 'directors'
    WRITER = 'writers'


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


def _build_filter_query(filter_by: FilterBy) -> Dict:
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


def _build_person_role_query(person_id: UUID) -> List:
    result = []
    for role in Roles:
        result.append({})
        result.append(
            {
                'query': {
                    'nested': {
                        'path': role.value,
                        'query': {
                            'match': {f'{role.value}.id': person_id}
                        }
                    }
                }
            })

    return result


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
                   page_number: int,
                   page_size: int,
                   sort_by: Optional[SortBy] = None,
                   filter_by: Optional[FilterBy] = None,) -> List[Film]:
        """
        Возвращает все фильмы.
        """
        # получаем только ID фильмов
        limit = page_size
        offset = page_size * (page_number - 1)
        film_ids = await self._es_get_all(offset, limit, sort_by, filter_by)
        # OrderedDict позволяет сохранить исходный порядок сортировки
        films = OrderedDict.fromkeys(film_ids, None)

        # проверяем есть ли полученные фильмы в кеше по их ID
        for film_id in films.keys():
            data = await self.cache.get(film_id)
            if data:
                films[film_id] = Film.parse_raw(data)

        # не найденные в кеше фильмы запрашиваем в эластике и кладём в кеш
        not_found = [film_id for film_id in films.keys()
                     if films[film_id] is None]
        if not_found:
            docs = await self._es_get_by_ids(not_found)
            for doc in docs:
                film = Film(**doc)
                await self.cache.put(film.id, film.json())
                films[film.id] = film
        return list(films.values())

    async def get_by_person_id(self, person_id: UUID) -> Dict[Roles, List[UUID]]:
        film_by_role = await self._es_get_by_person(person_id)
        return film_by_role

    async def _es_get_by_ids(self, film_ids: List[UUID]) -> List[dict]:
        """
        Получает фильмы из elasticsearch по списку id
        """
        doc_ids = [{'_id': film_id} for film_id in film_ids]
        resp = await self.elastic.mget(index=FILMS_INDEX, body={'docs': doc_ids})
        docs = [doc['_source'] for doc in resp['docs']]
        return docs

    async def _es_get_all(self,
                          offset: int,
                          limit: int,
                          sort_by: Optional[SortBy] = None,
                          filter_by: Optional[FilterBy] = None) -> List[UUID]:
        """
        Возвращает список id фильмов из elasticsearch с учётом сортировки и фильтрации
        """
        params = {"_source": False, "size": limit, "from": offset}
        if sort_by:
            params.update({'sort': f'{sort_by.attr}:{sort_by.order.value}'})
        body = None
        if filter_by:
            body = _build_filter_query(filter_by)
        docs = await self.elastic.search(index=FILMS_INDEX, params=params, body=body)
        ids = [UUID(doc['_id']) for doc in docs['hits']['hits']]
        return ids

    async def _es_get_by_person(self, person_id: UUID) -> Dict[Roles, List[UUID]]:
        """
        Возвращает список id фильмов из elasticsearch в которых участовала
        указанная персона
        """
        body = _build_person_role_query(person_id)
        docs = await self.elastic.msearch(index=FILMS_INDEX, body=body)
        actor, writer, director = docs['responses']
        films = {}
        films[Roles.ACTOR.value] = [UUID(doc['_id'])
                                    for doc in actor['hits']['hits']]
        films[Roles.WRITER.value] = [UUID(doc['_id'])
                                     for doc in writer['hits']['hits']]
        films[Roles.DIRECTOR.value] = [UUID(doc['_id'])
                                       for doc in director['hits']['hits']]
        return films


@lru_cache()
def get_film_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    return FilmService(RedisCache(redis=redis,
                                  keybuilder=films_keybuilder),
                       elastic)
