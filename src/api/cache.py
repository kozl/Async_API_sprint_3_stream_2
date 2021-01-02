from functools import wraps
from typing import Optional, List
from collections.abc import Iterable
import json

from fastapi import Depends, Request
from aioredis import Redis

from db.redis import get_redis

DEFAULT_TTL = 60


def build_key(func, query_args, *args, **kwargs) -> str:
    """
    Формирует ключ для хранения данных в кеше.
    Если среди параметров функции есть объъект Response, использует
    query_args для формирования ключа (для функций, которые используют Response для получения параметров запроса)
    """
    kwargs_key = {k: v for k, v in kwargs.items() if k in query_args}
    for k, v in kwargs.items():
        if isinstance(v, Request):
            kwargs_key['query_params'] = v.query_params
    return f'response:{func.__module__}.{func.__name__}:{args}:{kwargs_key}'


def cache_response(
    ttl: Optional[int] = DEFAULT_TTL,
    query_args: List[str] = [],
):
    """
    Декоратор для кеширования ответа метода API

    ttl: время жизни записи в кеш
    query_args: аргументы метода API, которые меняют его поведение
    """
    def wrapper(func):
        @wraps(func)
        async def inner(*args, **kwargs):
            nonlocal ttl
            nonlocal query_args

            redis = await get_redis()
            cache_key = build_key(func, query_args, *args, **kwargs)
            resp = await redis.get(cache_key)
            if resp:
                return json.loads(resp)
            ret = await func(*args, **kwargs)
            await redis.set(cache_key, ret.json(), expire=ttl)
            return ret
        return inner
    return wrapper
