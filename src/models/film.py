from typing import List, Optional
from uuid import UUID

import orjson

# Используем pydantic для упрощения работы при перегонке данных из json в объекты
from pydantic import BaseModel


def orjson_dumps(v, *, default):
    # orjson.dumps returns bytes, to match standard json.dumps we need to decode
    return orjson.dumps(v, default=default).decode()


class Film(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    imdb_rating: float
    type: str
    directors_names: str
    actors_names: str
    writers_names: str
    # genres: List[Genre]
    # actors: List[Actor]
    # writers: List[Writer]
    # directors: List[Director]

    class Config:
        # Заменяем стандартную работу с json на более быструю
        json_loads = orjson.loads
        json_dumps = orjson_dumps
