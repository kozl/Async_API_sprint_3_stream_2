from enum import Enum
from uuid import UUID
from typing import List, Optional
from functools import lru_cache
from collections import OrderedDict

from fastapi import Depends
from aioredis import Redis
from elasticsearch import AsyncElasticsearch

from db.elastic import get_elastic
from db.redis import get_redis
from cache.redis import RedisCache
from models.person import Person
from core import settings
import logging

logger = logging.getLogger(__name__)


PERSONS_INDEX = 'persons'


class Roles(Enum):
    ACTOR = 'actors'
    DIRECTOR = 'directors'
    WRITER = 'writers'


def persons_keybuilder(person_id: UUID) -> str:
    return f'person:{str(person_id)}'


def _build_person_serch_query(name: UUID) -> List:

    query = {
            'query': {
                'match': {
                    'name': {
                        'query': name,
                        'fuzziness': 'auto'
                    }
                }
            }
            }

    return query


class PersonService:

    def __init__(self, cache: RedisCache, elastic: AsyncElasticsearch):
        self.cache = cache
        self.elastic = elastic

    async def list(self,
                   page_number: int,
                   page_size: int) -> List[Person]:
        """
        Возвращает все персоны
        """
        # получаем только ID персон
        limit = page_size
        offset = page_size * (page_number - 1)
        person_ids = await self._es_get_all(offset, limit)
        persons = OrderedDict.fromkeys(person_ids, None)

        # проверяем есть ли полученные персоны в кеше по их ID
        for person_id in persons.keys():
            data = await self.cache.get(person_id)
            if data:
                persons[person_id] = Person.parse_raw(data)

        # не найденные в кеше персоны запрашиваем в эластике и кладём в кеш
        not_found = [person_id for person_id in persons.keys()
                     if persons[person_id] is None]
        if not_found:
            docs = await self._es_get_by_ids(not_found)
            for doc in docs:
                person = Person(**doc)
                await self.cache.put(person.id, person.json())
                persons[person.id] = person
        return list(persons.values())

    async def get_by_id(self, person_id: UUID) -> Optional[Person]:

        """
        Возвращает объект персоны. Он опционален, так как
        персона может отсутствовать в базе
        """

        data = await self.cache.get(person_id)
        if data:
            return Person.parse_raw(data)

        docs = await self._es_get_by_ids([person_id, ])
        if not docs:
            return None
        person = Person(**docs[0])
        await self.cache.put(person.id, person.json())
        return person

    async def get_by_name(self, name: str) -> Optional[List[Person]]:
        persons_result = []
        person_ids = await self._es_search_by_word(name)
        logger.debug('person_ids: %s', person_ids)
        if not person_ids:
            return None

        docs = await self._es_get_by_ids(person_ids)
        for doc in docs:
            persons_result.append(await self.get_by_id(doc['id']))

        return persons_result

    async def _es_search_by_word(self, name: str) -> List[dict]:
        params = {"_source": False}
        body = _build_person_serch_query(name)
        docs = await self.elastic.search(index=PERSONS_INDEX, body=body, params=params)
        ids = [UUID(doc['_id']) for doc in docs['hits']['hits']]
        return ids

    async def _es_get_by_ids(self, person_ids: List[UUID]) -> List[dict]:
        """
        Получает персоны из elasticsearch по списку id
        """
        doc_ids = [{'_id': person_id} for person_id in person_ids]
        resp = await self.elastic.mget(index=PERSONS_INDEX, body={'docs': doc_ids})
        docs = [doc['_source'] for doc in resp['docs']]
        return docs

    async def _es_get_all(self,
                          offset: int,
                          limit: int) -> List[UUID]:
        """
        Возвращает список id персон из elasticsearch с учётом сортировки и фильтрации
        """
        params = {"_source": False, "size": limit, "from": offset}
        docs = await self.elastic.search(index=PERSONS_INDEX, params=params)
        ids = [UUID(doc['_id']) for doc in docs['hits']['hits']]
        return ids


@ lru_cache()
def get_person_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic)


) -> PersonService:
    return PersonService(RedisCache(redis=redis,
                                    keybuilder=persons_keybuilder),
                         elastic)
