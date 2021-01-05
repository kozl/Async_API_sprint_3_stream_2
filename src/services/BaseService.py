import re
from typing import Optional, List
from uuid import UUID
from enum import Enum

from aioredis import Redis
from elasticsearch import AsyncElasticsearch
from pydantic import BaseModel
from starlette.datastructures import QueryParams


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
    attr: str = 'imdb_rating'
    order: SortOrder = SortOrder.DESC

    @classmethod
    def from_param(cls, param: str):
        """
        Парсит параметр, переданный в query и возвращает SortBy
        """
        if not param:
            return cls()
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


class BaseService:

    def __init__(self, redis: Redis, elastic: AsyncElasticsearch, index: str, model: BaseModel):
        self.redis = redis
        self.elastic = elastic
        self.index = index
        self.model = model

    # async def get_entitie_by_id(self, entitie_id: UUID) -> Optional[BaseModel]:
    async def get_by_id(self, entitie_id: UUID) -> Optional[BaseModel]:
        """
        Возвращает объект. Он опционален, так как
        сущность может отсутствовать в базе
        """
        entitie = await self._get_entitie_from_cache(entitie_id)
        if not entitie:
            entitie = await self._get_entitie_from_elastic(entitie_id)
            if not entitie:
                return None
            await self._put_entitie_to_cache(entitie)

        return entitie

    async def list(self,
                   sort_by: Optional[SortBy] = None,
                   filter_by: Optional[FilterBy] = None) -> List[BaseModel]:
        """
        Возвращает все сущности
        """
        entitie_ids = await self._list_entitie_ids_from_elastic(sort_by, filter_by)
        not_found = []
        result = []
        for entitie_id in entitie_ids:
            entitie = await self._get_entitie_from_cache(entitie_id)
            if not entitie:
                not_found.append(entitie_id)
            else:
                result.append(entitie_id)
        # не найденные в кеше фильмы запрашиваем в эластике и кладём в кеш
        if not_found:
            entities = await self._get_entities_from_elastic(not_found)
            for entitie in entities:
                await self._put_entitie_to_cache(entitie)
                result.append(entitie)
        return result

    async def _get_entities_from_elastic(self, entitie_ids: List[UUID]) -> List[BaseModel]:
        """
        Получает сущности из elasticsearch по списку id
        """
        doc_ids = [{'_id': id} for id in entitie_ids]
        resp = await self.elastic.mget(index=self.index, body={'docs': doc_ids})
        entities = [self.model(**doc['_source']) for doc in resp['docs']]
        return entities

    async def _get_entitie_from_elastic(self, entitie_id: UUID) -> Optional[BaseModel]:
        """
        Получает сущность из elasticsearch по id
        """
        doc = await self.elastic.get(self.index, entitie_id)
        return self.model(**doc['_source'])

    async def _list_entitie_ids_from_elastic(self,
                                             sort_by: Optional[SortBy] = None,
                                             filter_by: Optional[FilterBy] = None) -> List[UUID]:
        """
        Возвращает список id сущностей из elasticsearch с учётом сортировки и фильтрации
        """
        params = {"_source": False, "size": DEFAULT_LIST_SIZE}
        body = None

        if sort_by:
            params.update({'sort': f'{sort_by.attr}:{sort_by.order.value}'})

        if filter_by:
            body = _build_query(filter_by)

        docs = await self.elastic.search(index=self.index, params=params, body=body)
        ids = [doc['_id'] for doc in docs['hits']['hits']]
        return ids

    async def _get_entitie_from_cache(self, entitie_id: UUID) -> Optional[BaseModel]:
        """
        Отдаёт сущность из кеша по id
        """
        data = await self.redis.get(str(id))
        if not data:
            return None

        entitie = self.model.parse_raw(data)
        return entitie

    async def _put_entitie_to_cache(self, entitie: BaseModel) -> None:
        """
        Сохраняет сущность в кеш
        """
        await self.redis.set(str(entitie.id), entitie.json(), expire=FILM_CACHE_EXPIRE_IN_SECONDS)
