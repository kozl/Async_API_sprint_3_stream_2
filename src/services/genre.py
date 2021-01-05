from functools import lru_cache

from aioredis import Redis
from elasticsearch import AsyncElasticsearch
from fastapi import Depends


from db.elastic import get_elastic
from db.redis import get_redis
from models.genre import Genre

from services.BaseService import BaseService

FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут
DEFAULT_LIST_SIZE = 1000


class GenreService(BaseService):
    pass


@lru_cache()
def get_genre_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> GenreService:
    return GenreService(redis, elastic, 'genres', Genre)
