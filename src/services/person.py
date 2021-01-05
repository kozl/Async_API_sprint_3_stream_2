from services.BaseService import BaseService
from models.person import Person
from functools import lru_cache
from fastapi import Depends

from db.elastic import get_elastic
from db.redis import get_redis

from aioredis import Redis
from elasticsearch import AsyncElasticsearch

from enum import Enum
from uuid import UUID

from typing import List

DEFAULT_LIST_SIZE = 1000


class Roles(Enum):
    ACTOR = 'actors'
    DIRECTOR = 'directors'
    WRITER = 'writers'


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


class PersonService(BaseService):

    async def get_person_by_id(self, entitie_id: UUID):
        roles = {}
        init_person = (await self.get_by_id(entitie_id)).dict()
        body = _build_person_role_query(entitie_id)
        docs = await self.elastic.msearch(index='movies', body=body)

        actor, writer, director = docs['responses']

        roles['actor'] = [doc['_id'] for doc in actor['hits']['hits']]
        roles['writer'] = [doc['_id'] for doc in writer['hits']['hits']]
        roles['director'] = [doc['_id'] for doc in director['hits']['hits']]

        init_person.update(roles)
        person = Person(**init_person)
        print(person)

        return person


@lru_cache()
def get_person_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic)
) -> PersonService:
    return PersonService(redis, elastic, 'persons', Person)
