from enum import Enum
from uuid import UUID
from typing import List, Optional
from functools import lru_cache

from fastapi import Depends
from aioredis import Redis
from elasticsearch import AsyncElasticsearch

from db.elastic import get_elastic
from db.redis import get_redis
from cache.redis import RedisCache
from models.person import Person

DEFAULT_LIST_SIZE = 1000


class Roles(Enum):
    ACTOR = 'actors'
    DIRECTOR = 'directors'
    WRITER = 'writers'


def persons_keybuilder(person_id: UUID) -> str:
    return f'person:{str(person_id)}'


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


class PersonService:

    def __init__(self, cache: RedisCache, elastic: AsyncElasticsearch):
        self.cache = cache
        self.elastic = elastic

    async def list(self) -> List[Person]:
        """
        Возвращает все персоны
        """
        person_ids = await self._es_get_all()
        not_found = []
        result = []
        for person_id in person_ids:
            data = await self.cache.get(person_id)
            if not data:
                not_found.append(person_id)
            else:
                result.append(Person.parse_raw(data))
        # не найденные в кеше фильмы запрашиваем в эластике и кладём в кеш
        if not_found:
            docs = await self._es_get_by_ids(not_found)
            for doc in docs:
                person = Person(**doc)
                await self.cache.put(person.id, person.json())
                result.append(person)
        return result

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

    async def _es_get_by_ids(self, person_ids: List[UUID]) -> List[dict]:
        """
        Получает персоны из elasticsearch по списку id
        """
        doc_ids = [{'_id': person_id} for person_id in person_ids]
        resp = await self.elastic.mget(index='persons', body={'docs': doc_ids})
        docs = [doc['_source'] for doc in resp['docs']]
        return docs

    async def _es_get_all(self) -> List[UUID]:
        """
        Возвращает список id персон из elasticsearch с учётом сортировки и фильтрации
        """
        params = {"_source": False, "size": DEFAULT_LIST_SIZE}
        docs = await self.elastic.search(index='persons', params=params)
        ids = [UUID(doc['_id']) for doc in docs['hits']['hits']]
        return ids

    # async def get_by_id(self, person_id: UUID):
    #     roles = {}
    #     init_person = (await self.get_by_id(entitie_id)).dict()
    #     body = _build_person_role_query(entitie_id)
    #     docs = await self.elastic.msearch(index='movies', body=body)

    #     actor, writer, director = docs['responses']

    #     roles['actor'] = [doc['_id'] for doc in actor['hits']['hits']]
    #     roles['writer'] = [doc['_id'] for doc in writer['hits']['hits']]
    #     roles['director'] = [doc['_id'] for doc in director['hits']['hits']]

    #     init_person.update(roles)
    #     person = Person(**init_person)
    #     print(person)

    #     return person


@lru_cache()
def get_person_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic)
) -> PersonService:
    return PersonService(RedisCache(redis=redis,
                                    keybuilder=persons_keybuilder),
                         elastic)
